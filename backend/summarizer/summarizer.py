import logging
import re
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# POURQUOI CE PIPELINE EN 3 ETAPES (FR -> EN -> resume -> EN -> FR) :
#
# facebook/bart-large-cnn est un modele de resume ENTRAINE UNIQUEMENT EN
# ANGLAIS. Lui donner du texte francais en entree ne produit jamais un
# resume grammaticalement correct : le modele "comprend" mal la structure
# de la phrase francaise, d'ou les mots anglais infiltres et les tournures
# cassees ("sur y trouve" au lieu de "on y trouve"). Corriger ca avec des
# regex mot-a-mot (_corriger_mots_anglais / _supprimer_phrases_anglaises,
# retirees ici) ne peut JAMAIS reparer l'accord, la conjugaison ou l'ordre
# des mots : ce n'est pas de la grammaire, c'est du remplacement de tokens.
#
# On isole donc le probleme de langue dans deux modeles de TRADUCTION
# dedies (Helsinki-NLP/opus-mt-fr-en et opus-mt-en-fr), chacun ~300 Mo,
# donc bien plus legers et plus fiables a telecharger que barthez-orangesum
# (557 Mo, bloque). Le pipeline de resume dichotomique existant (qui
# fonctionne bien) reste inchange et continue de tourner sur du texte
# anglais, son terrain naturel.
# ---------------------------------------------------------------------------

SUMMARY_MODEL_NAME = "facebook/bart-large-cnn"

# Resolution des modeles de traduction : si le dossier local existe (deja
# telecharge a la main dans backend/models/, cas de developpement avec une
# connexion instable), on l'utilise directement sans passer par internet.
# Sinon, on retombe sur le nom HuggingFace standard, que `transformers`
# telechargera et mettra en cache automatiquement (cas normal pour un
# coequipier ou le jury avec une connexion stable).
# IMPORTANT : backend/models/ est dans le .gitignore et n'est donc PAS
# pousse sur GitHub (trop volumineux, ~600 Mo). Chaque machine se debrouille
# soit avec ses propres fichiers locaux, soit avec le telechargement auto.
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_LOCAL_MODELS_DIR = _os.path.join(_BACKEND_DIR, "models")


def _resolve_model_path(hf_name: str, local_dirname: str) -> str:
    local_path = _os.path.join(_LOCAL_MODELS_DIR, local_dirname)
    if _os.path.isdir(local_path) and _os.listdir(local_path):
        logger.info(f"Modele local trouve pour {hf_name} -> {local_path}")
        return local_path
    logger.info(f"Pas de modele local pour {hf_name}, telechargement HuggingFace si necessaire.")
    return hf_name


TRANSLATION_MODEL_FR_EN = _resolve_model_path("Helsinki-NLP/opus-mt-fr-en", "opus-mt-fr-en")
TRANSLATION_MODEL_EN_FR = _resolve_model_path("Helsinki-NLP/opus-mt-en-fr", "opus-mt-en-fr")
MODEL_PROMPT_PREFIX = ""

# Alias conserve pour compatibilite si d'autres fichiers importent DEFAULT_MODEL_NAME
DEFAULT_MODEL_NAME = SUMMARY_MODEL_NAME

MIN_CHUNK_TOKENS = 50
SAFETY_MARGIN = 20

RATIO_MIN = 0.30
RATIO_MAX = 0.40
MIN_LENGTH_RATIO = RATIO_MIN / RATIO_MAX

TOKENS_PER_WORD_FACTOR = 1.4


class SummarizationError(Exception):
    pass


def _terminer_proprement(texte: str) -> str:
    matches = list(re.finditer(r'[.!?]', texte))
    if matches:
        dernier_point = matches[-1].end()
        return texte[:dernier_point].strip()
    return texte.strip()


def _compter_mots(texte: str) -> int:
    return len(texte.split())


def _tronquer_a_la_limite(texte: str, max_mots: int) -> str:
    mots = texte.split()
    if len(mots) <= max_mots:
        return texte.strip()
    tronque = " ".join(mots[:max_mots])
    propre = _terminer_proprement(tronque)
    if not propre or not re.search(r'[.!?]$', propre):
        propre = tronque.rstrip(" ,;:") + "."
    return propre


@lru_cache(maxsize=1)
def _get_summary_pipeline(model_name: str = SUMMARY_MODEL_NAME):
    try:
        from transformers import pipeline
        import torch
        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Chargement du modele de resume : {model_name} (device={device})")
        return pipeline("summarization", model=model_name, device=device)
    except Exception as e:
        raise SummarizationError(f"Impossible de charger le pipeline de resume : {e}")


@lru_cache(maxsize=2)
def _get_translation_pipeline(model_name: str):
    try:
        from transformers import pipeline
        import torch
        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Chargement du modele de traduction : {model_name} (device={device})")
        return pipeline("translation", model=model_name, device=device)
    except Exception as e:
        raise SummarizationError(f"Impossible de charger le pipeline de traduction ({model_name}) : {e}")


def _get_model_max_tokens(pipeline_obj) -> int:
    model_max = getattr(pipeline_obj.tokenizer, "model_max_length", 1024)
    if not model_max or model_max > 100000:
        model_max = 1024
    return model_max


def _decouper_par_dichotomie(pipeline_obj, text: str, max_tokens: int) -> List[str]:
    tokenizer = pipeline_obj.tokenizer
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    sous_parties = []
    for i in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text.strip():
            sous_parties.append(chunk_text)
    return sous_parties


def _traduire(texte: str, model_name: str) -> str:
    """Traduit un texte (potentiellement long) en le decoupant par dichotomie,
    comme pour le resume, afin de respecter la limite de tokens du modele."""
    if not texte or not texte.strip():
        return ""
    pipe = _get_translation_pipeline(model_name)
    model_max = _get_model_max_tokens(pipe)
    max_chunk = max(model_max - SAFETY_MARGIN, MIN_CHUNK_TOKENS)
    morceaux = _decouper_par_dichotomie(pipe, texte, max_chunk)
    traductions = []
    for morceau in morceaux:
        try:
            resultat = pipe(morceau, max_length=max_chunk)
            traductions.append(resultat[0]["translation_text"].strip())
        except Exception as e:
            raise SummarizationError(f"Erreur pendant la traduction ({model_name}) : {e}")
    return " ".join(t for t in traductions if t)


def _compute_target_length(word_count: int):
    target_max = max(1, int(word_count * RATIO_MAX))
    target_min = max(1, int(word_count * RATIO_MIN))
    if target_min >= target_max:
        target_min = max(1, target_max - 1)
    return target_max, target_min


def _resumer_sous_partie(pipeline_obj, chunk: str, max_length_words: int, min_length_words: int) -> str:
    word_count = len(chunk.split())
    max_length_tokens = int(max_length_words * TOKENS_PER_WORD_FACTOR)
    min_length_tokens = int(min_length_words * TOKENS_PER_WORD_FACTOR)
    safe_max = min(max_length_tokens, max(word_count, MIN_CHUNK_TOKENS))
    safe_min = min(min_length_tokens, safe_max - 1) if safe_max > 1 else 1
    prompted_chunk = f"{MODEL_PROMPT_PREFIX}{chunk}" if MODEL_PROMPT_PREFIX else chunk

    try:
        result = pipeline_obj(
            prompted_chunk, max_length=safe_max, min_length=safe_min,
            do_sample=False, num_beams=4, no_repeat_ngram_size=3, truncation=True,
        )
        texte_resume = result[0]["summary_text"].strip()
        texte_resume = _terminer_proprement(texte_resume)
        if _compter_mots(texte_resume) > max_length_words:
            texte_resume = _tronquer_a_la_limite(texte_resume, max_length_words)
        return texte_resume
    except Exception as e:
        raise SummarizationError(f"Erreur pendant la generation du resume : {e}")


def _resumer_en_anglais(text_en: str, final_max_length: int, final_min_length: int, model_name: str) -> str:
    """Applique le pipeline dichotomique existant (inchange) sur du texte anglais."""
    pipeline_obj = _get_summary_pipeline(model_name)
    model_max = _get_model_max_tokens(pipeline_obj)
    taille_max_sous_partie = model_max - SAFETY_MARGIN

    texte_courant = text_en
    niveau_dichotomie = 1

    while True:
        sous_parties = _decouper_par_dichotomie(pipeline_obj, texte_courant, taille_max_sous_partie)

        if len(sous_parties) == 1:
            return _resumer_sous_partie(pipeline_obj, sous_parties[0], final_max_length, final_min_length)

        resumes_partiels = []
        for partie in sous_parties:
            mots_partie = len(partie.split())
            cible_max, cible_min = _compute_target_length(mots_partie)
            resumes_partiels.append(_resumer_sous_partie(pipeline_obj, partie, cible_max, cible_min))

        texte_courant = " ".join(resumes_partiels)
        niveau_dichotomie += 1

        if niveau_dichotomie > 15:
            return _resumer_sous_partie(pipeline_obj, texte_courant, final_max_length, final_min_length)


def summarize_text(
    text: str,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    model_name: str = SUMMARY_MODEL_NAME,
) -> str:
    if not text or not text.strip():
        raise SummarizationError("Le texte a resumer est vide.")

    original_word_count = len(text.split())

    if max_length is None:
        final_max_length_fr, final_min_length_fr = _compute_target_length(original_word_count)
    else:
        final_max_length_fr = max_length
        final_min_length_fr = min_length if min_length is not None else max(1, int(max_length * MIN_LENGTH_RATIO))

    logger.info(
        f"Document de {original_word_count} mots (FR) -> cible finale : "
        f"{final_min_length_fr}-{final_max_length_fr} mots (30%-40%)."
    )

    # Etape 1 : FR -> EN
    logger.info("Traduction FR -> EN...")
    texte_en = _traduire(text, TRANSLATION_MODEL_FR_EN)
    if not texte_en.strip():
        raise SummarizationError("La traduction FR->EN a produit un texte vide.")

    mots_en = len(texte_en.split())
    cible_max_en, cible_min_en = _compute_target_length(mots_en)

    # On tente jusqu'a 2 fois : si le resume final francais est trop court
    # par rapport a la cible 30%-40%, on relance avec une cible anglaise
    # plus genereuse (le modele de resume ne respecte pas toujours son
    # min_length a l'octet pres, et la traduction retour peut aussi
    # compresser legerement la formulation).
    resume_fr = ""
    for tentative in range(2):
        logger.info(
            f"[Tentative {tentative + 1}] Resume EN sur {mots_en} mots -> "
            f"cible {cible_min_en}-{cible_max_en} mots..."
        )
        resume_en = _resumer_en_anglais(texte_en, cible_max_en, cible_min_en, model_name)

        logger.info("Traduction EN -> FR du resume...")
        resume_fr = _traduire(resume_en, TRANSLATION_MODEL_EN_FR)
        resume_fr = _terminer_proprement(resume_fr)

        mots_resume_fr = _compter_mots(resume_fr)

        if mots_resume_fr > final_max_length_fr:
            resume_fr = _tronquer_a_la_limite(resume_fr, final_max_length_fr)
            break

        if mots_resume_fr >= final_min_length_fr:
            break

        # Resume trop court : on augmente la cible anglaise proportionnellement
        # au manque constate, puis on relance une seule fois.
        if tentative == 0 and mots_resume_fr > 0:
            facteur = final_min_length_fr / mots_resume_fr
            cible_min_en = min(int(cible_min_en * facteur * 1.15), mots_en)
            cible_max_en = min(int(cible_max_en * facteur * 1.15), mots_en)
            if cible_min_en >= cible_max_en:
                cible_max_en = cible_min_en + 5
            logger.info(
                f"Resume trop court ({mots_resume_fr} mots, cible min "
                f"{final_min_length_fr}) -> nouvelle cible EN {cible_min_en}-{cible_max_en}."
            )

    if not resume_fr.strip():
        raise SummarizationError("Le resume final est vide apres traduction.")

    mots_finaux = _compter_mots(resume_fr)
    logger.info(f"Resume final : {mots_finaux} mots (cible {final_min_length_fr}-{final_max_length_fr}).")
    if not (final_min_length_fr <= mots_finaux <= final_max_length_fr):
        logger.warning(
            f"Le ratio final ({mots_finaux} mots) reste hors de la cible "
            f"30%-40% ({final_min_length_fr}-{final_max_length_fr} mots) apres relance."
        )

    return resume_fr
