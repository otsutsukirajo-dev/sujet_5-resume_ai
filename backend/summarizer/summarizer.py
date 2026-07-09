
import logging
import math
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)

# Modèle par défaut. mBART/mT5 seraient de meilleurs choix pour du
# français/malgache multilingue, mais BART-CNN est un bon point de
# départ rapide en anglais. À ajuster selon les tests de l'équipe.
DEFAULT_MODEL_NAME = "facebook/bart-large-cnn"

# Limite approximative de tokens que le modèle peut ingérer d'un coup.
MAX_CHUNK_TOKENS = 900
MIN_CHUNK_TOKENS = 50


class SummarizationError(Exception):
    """Levée quand la génération de résumé échoue."""
    pass


@lru_cache(maxsize=1)
def _get_pipeline(model_name: str = DEFAULT_MODEL_NAME):
    """
    Charge (une seule fois, via cache) le pipeline de résumé transformers.
    Le lru_cache évite de recharger le modèle en mémoire à chaque appel.
    """
    try:
        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Chargement du modèle de résumé : {model_name} (device={device})")
        return pipeline("summarization", model=model_name, device=device)
    except Exception as e:
        raise SummarizationError(
            f"Impossible de charger le pipeline de résumé : {e}"
        )


def _split_into_chunks(text: str, max_words: int = 700) -> List[str]:
    """
    Découpe un texte long en morceaux traitables par le modèle,
    en respectant les frontières de phrases (découpage naïf sur '.').
    """
    sentences = text.replace("\n", " ").split(". ")
    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        word_count = len(sentence.split())
        if current_len + word_count > max_words and current_chunk:
            chunks.append(". ".join(current_chunk).strip() + ".")
            current_chunk = [sentence]
            current_len = word_count
        else:
            current_chunk.append(sentence)
            current_len += word_count

    if current_chunk:
        chunks.append(". ".join(current_chunk).strip())

    return [c for c in chunks if c.strip()]


def summarize_text(
    text: str,
    max_length: int = 150,
    min_length: int = 40,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """
    Génère un résumé du texte fourni.

    Args:
        text: texte source à résumer (déjà extrait par extractor.py).
        max_length: longueur max du résumé (en tokens).
        min_length: longueur min du résumé (en tokens).
        model_name: nom du modèle HuggingFace à utiliser.

    Returns:
        Le résumé généré (str).

    Raises:
        SummarizationError: si le texte est vide ou si le modèle échoue.
    """
    if not text or not text.strip():
        raise SummarizationError("Le texte à résumer est vide.")

    summarizer_pipeline = _get_pipeline(model_name)

    chunks = _split_into_chunks(text)

    if len(chunks) == 1:
        return _summarize_chunk(summarizer_pipeline, chunks[0], max_length, min_length)

    # Texte long : on résume chaque morceau, puis on résume la
    # concaténation des résumés partiels (map-reduce).
    logger.info(f"Texte découpé en {len(chunks)} morceaux pour le résumé.")
    partial_summaries = [
        _summarize_chunk(summarizer_pipeline, chunk, max_length=100, min_length=30)
        for chunk in chunks
    ]
    combined = " ".join(partial_summaries)

    # Si le résumé combiné est encore trop long, on le repasse une fois
    if len(combined.split()) > max_length * 2:
        return _summarize_chunk(summarizer_pipeline, combined, max_length, min_length)

    return combined


def _summarize_chunk(pipeline_obj, chunk: str, max_length: int, min_length: int) -> str:
    """Appelle le pipeline sur un seul morceau de texte, avec garde-fous."""
    word_count = len(chunk.split())
    # Évite les erreurs si min_length > longueur du texte source
    safe_max = min(max_length, max(word_count, MIN_CHUNK_TOKENS))
    safe_min = min(min_length, safe_max - 1) if safe_max > 1 else 1

    try:
        result = pipeline_obj(
            chunk,
            max_length=safe_max,
            min_length=safe_min,
            do_sample=False,
            truncation=True,
        )
        return result[0]["summary_text"].strip()
    except Exception as e:
        raise SummarizationError(f"Erreur pendant la génération du résumé : {e}")