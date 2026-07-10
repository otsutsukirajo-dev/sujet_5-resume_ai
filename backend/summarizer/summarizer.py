import logging
import re
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger(__name__)

CORRECTIONS_ANGLAIS_FRANCAIS = {
    r"\bfor\b": "pour",
    r"\band\b": "et",
    r"\bthe\b": "le",
    r"\bof\b": "de",
    r"\bis\b": "est",
    r"\bare\b": "sont",
    r"\bwith\b": "avec",
    r"\bthis\b": "ce",
    r"\bthat\b": "que",
    r"\bit\b": "il",
    r"\bin\b": "dans",
    r"\bon\b": "sur",
    r"\bto\b": "à",
    # "as" retire : conjugaison de "avoir" en francais ("tu as fini")
    r"\bfrom\b": "de",
    r"\bbut\b": "mais",
    r"\bnot\b": "pas",
    r"\bhas\b": "a",
    r"\bhave\b": "ont",
    r"\bwas\b": "était",
    r"\bwere\b": "étaient",
    r"\bwhich\b": "qui",
    r"\bwhile\b": "tandis que",
    r"\bthey\b": "ils",
    r"\btheir\b": "leur",
    r"\bby\b": "par",
    r"\bpublished\b": "publié",
    r"\bpriced\b": "au prix de",
    r"\bpress\b": "édition",
    r"\bbook\b": "livre",
    r"\buniversity\b": "université",
    r"\bauthor\b": "auteur",
    r"\bpage\b": "page",
    r"\bpages\b": "pages",
    r"\bedition\b": "édition",
    r"\bavailable\b": "disponible",
    r"\bincludes\b": "inclut",
}


def _corriger_mots_anglais(texte: str) -> str:
    for pattern_anglais, mot_francais in CORRECTIONS_ANGLAIS_FRANCAIS.items():
        texte = re.sub(pattern_anglais, mot_francais, texte, flags=re.IGNORECASE)
    return texte


def _supprimer_phrases_anglaises(texte: str) -> str:
    mots_anglais_indicateurs = {
        "the", "is", "are", "was", "were", "by", "published", "press",
        "priced", "university", "book", "author", "available", "with",
        "and", "for", "this", "that", "which", "of", "in", "to",
        # "on" retire : pronom francais tres courant
    }

    phrases = re.split(r'(?<=[.!?])\s+', texte)
    phrases_gardees = []

    for phrase in phrases:
        mots = re.findall(r"[a-zA-ZÀ-ÿ']+", phrase.lower())
        if not mots:
            continue
        nb_mots_anglais = sum(1 for m in mots if m in mots_anglais_indicateurs)

        if len(mots) < 8:
            est_hallucination = nb_mots_anglais >= 3
        else:
            proportion_anglaise = nb_mots_anglais / len(mots)
            est_hallucination = proportion_anglaise > 0.25

        if not est_hallucination:
            phrases_gardees.append(phrase)

    resultat = " ".join(phrases_gardees).strip()
    return resultat if resultat else texte.strip()


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


DEFAULT_MODEL_NAME = "facebook/bart-large-cnn"
MODEL_PROMPT_PREFIX = ""

MIN_CHUNK_TOKENS = 50
SAFETY_MARGIN = 20

RATIO_MIN = 0.30
RATIO_MAX = 0.40

MIN_LENGTH_RATIO = RATIO_MIN / RATIO_MAX

TOKENS_PER_WORD_FACTOR = 1.4

MAX_TENTATIVES_ALLONGEMENT = 2


class SummarizationError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_pipeline(model_name: str = DEFAULT_MODEL_NAME):
    try:
        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Chargement du modele de resume : {model_name} (device={device})")
        return pipeline("summarization", model=model_name, device=device)
    except Exception as e:
        raise SummarizationError(f"Impossible de charger le pipeline de resume : {e}")


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


def _compute_target_length(word_count: int):
    target_max = max(1, int(word_count * RATIO_MAX))
    target_min = max(1, int(word_count * RATIO_MIN))
    if target_min >= target_max:
        target_min = max(1, target_max - 1)
    return target_max, target_min


def _generer_resume_brut(pipeline_obj, chunk: str, safe_max: int, safe_min: int, length_penalty: float = 1.0) -> str:
    prompted_chunk = f"{MODEL_PROMPT_PREFIX}{chunk}" if MODEL_PROMPT_PREFIX else chunk
    try:
        result = pipeline_obj(
            prompted_chunk,
            max_length=safe_max,
            min_length=safe_min,
            do_sample=False,
            truncation=True,
            length_penalty=length_penalty,
        )
        return result[0]["summary_text"].strip()
    except Exception as e:
        raise SummarizationError(f"Erreur pendant la generation du resume : {e}")


def _resumer_sous_partie(pipeline_obj, chunk: str, max_length_words: int, min_length_words: int) -> str:
    word_count = len(chunk.split())

    max_length_tokens = int(max_length_words * TOKENS_PER_WORD_FACTOR)
    min_length_tokens = int(min_length_words * TOKENS_PER_WORD_FACTOR)

    safe_max = min(max_length_tokens, max(word_count, MIN_CHUNK_TOKENS))
    safe_min = min(min_length_tokens, safe_max - 1) if safe_max > 1 else 1

    texte_brut = _generer_resume_brut(pipeline_obj, chunk, safe_max, safe_min)

    tentative = 0
    while _compter_mots(texte_brut) < min_length_words and tentative < MAX_TENTATIVES_ALLONGEMENT:
        tentative += 1
        length_penalty = 1.0 + tentative
        texte_brut = _generer_resume_brut(pipeline_obj, chunk, safe_max, safe_min, length_penalty=length_penalty)


    candidat_brut_termine = _terminer_proprement(texte_brut)

    sans_phrases_ang = _supprimer_phrases_anglaises(texte_brut)
    candidat_nettoye_complet = _terminer_proprement(_corriger_mots_anglais(sans_phrases_ang))

    candidat_corrections_seules = _terminer_proprement(_corriger_mots_anglais(texte_brut))

    if _compter_mots(candidat_nettoye_complet) >= min_length_words:
        texte_final = candidat_nettoye_complet
    elif _compter_mots(candidat_corrections_seules) >= min_length_words:
        texte_final = candidat_corrections_seules
    else:
        texte_final = candidat_brut_termine
        if _compter_mots(texte_final) < min_length_words:
            logger.warning(
                f"Resume sous la borne minimale ({_compter_mots(texte_final)} mots "
                f"< {min_length_words} attendus) meme apres tentatives de rallonge."
            )

    if _compter_mots(texte_final) > max_length_words:
        texte_final = _tronquer_a_la_limite(texte_final, max_length_words)

    return texte_final


def summarize_text(
    text: str,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    if not text or not text.strip():
        raise SummarizationError("Le texte a resumer est vide.")

    original_word_count = len(text.split())
    ratio_strict_actif = max_length is None

    if max_length is None:
        final_max_length, final_min_length = _compute_target_length(original_word_count)
    else:
        final_max_length = max_length
        final_min_length = min_length if min_length is not None else max(1, int(max_length * MIN_LENGTH_RATIO))

    logger.info(
        f"Document de {original_word_count} mots -> cible : "
        f"{final_min_length}-{final_max_length} mots (30%-40% strict)."
    )

    pipeline_obj = _get_pipeline(model_name)
    model_max = _get_model_max_tokens(pipeline_obj)
    taille_max_sous_partie = model_max - SAFETY_MARGIN

    texte_courant = text
    niveau_dichotomie = 1
    resultat: Optional[str] = None

    while resultat is None:
        sous_parties = _decouper_par_dichotomie(pipeline_obj, texte_courant, taille_max_sous_partie)

        if len(sous_parties) == 1:
            logger.info(f"Resume final obtenu apres {niveau_dichotomie} niveau(x) de dichotomie.")
            resultat = _resumer_sous_partie(pipeline_obj, sous_parties[0], final_max_length, final_min_length)
            break

        logger.info(
            f"Niveau {niveau_dichotomie} de dichotomie : document divise en {len(sous_parties)} sous-parties."
        )

        resumes_partiels = []
        for partie in sous_parties:
            mots_partie = len(partie.split())
            cible_max, cible_min = _compute_target_length(mots_partie)
            resumes_partiels.append(_resumer_sous_partie(pipeline_obj, partie, cible_max, cible_min))

        texte_courant = " ".join(resumes_partiels)
        niveau_dichotomie += 1

        if niveau_dichotomie > 15:
            logger.warning("Nombre de niveaux de dichotomie eleve, arret force.")
            resultat = _resumer_sous_partie(pipeline_obj, texte_courant, final_max_length, final_min_length)
            break

    if ratio_strict_actif:
        mots_resultat = _compter_mots(resultat)
        if mots_resultat > final_max_length:
            resultat = _tronquer_a_la_limite(resultat, final_max_length)
        elif mots_resultat < final_min_length:
            logger.warning(
                f"Resume final sous la borne minimale ({mots_resultat} mots "
                f"< {final_min_length} attendus)."
            )

    return resultat
