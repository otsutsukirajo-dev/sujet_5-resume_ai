import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)

# MODELE : facebook/bart-large-cnn (deja en cache local, fonctionnel).
DEFAULT_MODEL_NAME = "facebook/bart-large-cnn"
MODEL_PROMPT_PREFIX = ""

MIN_CHUNK_TOKENS = 50
SAFETY_MARGIN = 20

SUMMARY_RATIO = 0.35
MIN_TARGET_WORDS = 250
MAX_TARGET_WORDS = 1200
MIN_LENGTH_RATIO = 0.55

PARTIAL_MIN_TARGET_WORDS = 80
PARTIAL_MAX_TARGET_WORDS = 300

TOKENS_PER_WORD_FACTOR = 1.4


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
    """
    Decoupe le texte source en sous-parties (dichotomie du document) dont
    la taille en TOKENS reste sous la limite du modele. Chaque sous-partie
    sera resumee independamment avant recombinaison.
    """
    tokenizer = pipeline_obj.tokenizer
    token_ids = tokenizer.encode(text, add_special_tokens=False)

    sous_parties = []
    for i in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text.strip():
            sous_parties.append(chunk_text)
    return sous_parties


def _compute_target_length(word_count: int, floor: int, ceiling: int, ratio: float = SUMMARY_RATIO):
    target_max = int(word_count * ratio)
    target_max = max(floor, min(ceiling, target_max))
    target_min = max(1, int(target_max * MIN_LENGTH_RATIO))
    if target_min >= target_max:
        target_min = max(1, target_max - 1)
    return target_max, target_min


def _resumer_sous_partie(pipeline_obj, chunk: str, max_length_words: int, min_length_words: int) -> str:
    """Genere le resume d'une seule sous-partie issue de la dichotomie."""
    word_count = len(chunk.split())

    max_length_tokens = int(max_length_words * TOKENS_PER_WORD_FACTOR)
    min_length_tokens = int(min_length_words * TOKENS_PER_WORD_FACTOR)

    safe_max = min(max_length_tokens, max(word_count, MIN_CHUNK_TOKENS))
    safe_min = min(min_length_tokens, safe_max - 1) if safe_max > 1 else 1

    prompted_chunk = f"{MODEL_PROMPT_PREFIX}{chunk}" if MODEL_PROMPT_PREFIX else chunk

    try:
        result = pipeline_obj(
            prompted_chunk,
            max_length=safe_max,
            min_length=safe_min,
            do_sample=False,
            truncation=True,
        )
        return result[0]["summary_text"].strip()
    except Exception as e:
        raise SummarizationError(f"Erreur pendant la generation du resume : {e}")


def summarize_text(
    text: str,
    max_length: int = 150,
    min_length: int = 40,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """
    Genere un resume, quelle que soit la longueur du texte source, par
    DICHOTOMIE RECURSIVE : le document est decoupe en sous-parties, chaque
    sous-partie est resumee independamment, les resumes partiels sont
    recombines en un nouveau texte, et on recommence la dichotomie sur ce
    nouveau texte tant qu'il ne tient pas en une seule sous-partie.
    """
    if not text or not text.strip():
        raise SummarizationError("Le texte a resumer est vide.")

    original_word_count = len(text.split())

    if max_length is None:
        final_max_length, computed_min = _compute_target_length(
            original_word_count, MIN_TARGET_WORDS, MAX_TARGET_WORDS
        )
        final_min_length = min_length if min_length is not None else computed_min
    else:
        final_max_length = max_length
        final_min_length = min_length if min_length is not None else max(40, int(max_length * MIN_LENGTH_RATIO))

    logger.info(
        f"Document de {original_word_count} mots -> cible : "
        f"{final_min_length}-{final_max_length} mots (ratio {SUMMARY_RATIO:.0%})."
    )

    pipeline_obj = _get_pipeline(model_name)
    model_max = _get_model_max_tokens(pipeline_obj)
    taille_max_sous_partie = model_max - SAFETY_MARGIN

    texte_courant = text
    niveau_dichotomie = 1

    while True:
        sous_parties = _decouper_par_dichotomie(pipeline_obj, texte_courant, taille_max_sous_partie)

        if len(sous_parties) == 1:
            logger.info(f"Resume final obtenu apres {niveau_dichotomie} niveau(x) de dichotomie.")
            return _resumer_sous_partie(pipeline_obj, sous_parties[0], final_max_length, final_min_length)

        logger.info(
            f"Niveau {niveau_dichotomie} de dichotomie : document divise en {len(sous_parties)} sous-parties."
        )

        resumes_partiels = []
        for partie in sous_parties:
            mots_partie = len(partie.split())
            cible_max, cible_min = _compute_target_length(
                mots_partie, PARTIAL_MIN_TARGET_WORDS, PARTIAL_MAX_TARGET_WORDS
            )
            resumes_partiels.append(_resumer_sous_partie(pipeline_obj, partie, cible_max, cible_min))

        texte_courant = " ".join(resumes_partiels)
        niveau_dichotomie += 1

        if niveau_dichotomie > 15:
            logger.warning("Nombre de niveaux de dichotomie eleve, arret force.")
            return _resumer_sous_partie(pipeline_obj, texte_courant, final_max_length, final_min_length)