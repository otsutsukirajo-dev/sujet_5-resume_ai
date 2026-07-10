import logging
from functools import lru_cache
from typing import List, Optional

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


def _split_into_token_chunks(pipeline_obj, text: str, max_tokens: int) -> List[str]:
    tokenizer = pipeline_obj.tokenizer
    token_ids = tokenizer.encode(text, add_special_tokens=False)

    chunks = []
    for i in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text.strip():
            chunks.append(chunk_text)
    return chunks


def _compute_target_length(word_count: int, floor: int, ceiling: int, ratio: float = SUMMARY_RATIO):
    target_max = int(word_count * ratio)
    target_max = max(floor, min(ceiling, target_max))
    target_min = max(1, int(target_max * MIN_LENGTH_RATIO))
    if target_min >= target_max:
        target_min = max(1, target_max - 1)
    return target_max, target_min


def _summarize_chunk(pipeline_obj, chunk: str, max_length_words: int, min_length_words: int) -> str:
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
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
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
    safe_chunk_tokens = model_max - SAFETY_MARGIN

    current_text = text
    pass_number = 1

    while True:
        chunks = _split_into_token_chunks(pipeline_obj, current_text, safe_chunk_tokens)

        if len(chunks) == 1:
            logger.info(f"Resume final genere en {pass_number} passe(s).")
            return _summarize_chunk(pipeline_obj, chunks[0], final_max_length, final_min_length)

        logger.info(f"Passe {pass_number} : document decoupe en {len(chunks)} morceaux.")

        partial_summaries = []
        for c in chunks:
            chunk_word_count = len(c.split())
            chunk_max, chunk_min = _compute_target_length(
                chunk_word_count, PARTIAL_MIN_TARGET_WORDS, PARTIAL_MAX_TARGET_WORDS
            )
            partial_summaries.append(_summarize_chunk(pipeline_obj, c, chunk_max, chunk_min))

        current_text = " ".join(partial_summaries)
        pass_number += 1

        if pass_number > 15:
            logger.warning("Nombre de passes eleve, arret force.")
            return _summarize_chunk(pipeline_obj, current_text, final_max_length, final_min_length)