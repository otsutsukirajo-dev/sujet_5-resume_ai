import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "facebook/bart-large-cnn"
MIN_CHUNK_TOKENS = 50
SAFETY_MARGIN = 20  # marge de sécurité en tokens sous la limite du modèle


class SummarizationError(Exception):
    """Levée quand la génération de résumé échoue."""
    pass


@lru_cache(maxsize=1)
def _get_pipeline(model_name: str = DEFAULT_MODEL_NAME):
    try:
        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Chargement du modèle de résumé : {model_name} (device={device})")
        return pipeline("summarization", model=model_name, device=device)
    except Exception as e:
        raise SummarizationError(f"Impossible de charger le pipeline de résumé : {e}")


def _get_model_max_tokens(pipeline_obj) -> int:
    model_max = getattr(pipeline_obj.tokenizer, "model_max_length", 1024)
    if not model_max or model_max > 100000:
        model_max = 1024  # valeur sûre par défaut pour bart-large-cnn
    return model_max


def _split_into_token_chunks(pipeline_obj, text: str, max_tokens: int) -> List[str]:
    """
    Découpe le texte en morceaux dont la taille en TOKENS (pas en mots)
    reste sous la limite du modèle. Fonctionne quelle que soit la mise
    en forme du document (listes, tableaux, symboles, formules tapées).
    """
    tokenizer = pipeline_obj.tokenizer
    token_ids = tokenizer.encode(text, add_special_tokens=False)

    chunks = []
    for i in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text.strip():
            chunks.append(chunk_text)
    return chunks


def _summarize_chunk(pipeline_obj, chunk: str, max_length: int, min_length: int) -> str:
    word_count = len(chunk.split())
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


def summarize_text(
    text: str,
    max_length: int = 150,
    min_length: int = 40,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """
    Génère un résumé, quelle que soit la longueur du texte source.
    Utilise une réduction récursive (map-reduce) : le document est
    découpé, chaque morceau est résumé, les résumés sont recombinés,
    et on recommence tant que le résultat ne tient pas en un seul bloc.
    """
    if not text or not text.strip():
        raise SummarizationError("Le texte à résumer est vide.")

    pipeline_obj = _get_pipeline(model_name)
    model_max = _get_model_max_tokens(pipeline_obj)
    safe_chunk_tokens = model_max - SAFETY_MARGIN

    current_text = text
    pass_number = 1

    while True:
        chunks = _split_into_token_chunks(pipeline_obj, current_text, safe_chunk_tokens)

        if len(chunks) == 1:
            logger.info(f"Résumé final généré en {pass_number} passe(s).")
            return _summarize_chunk(pipeline_obj, chunks[0], max_length, min_length)

        logger.info(
            f"Passe {pass_number} : document découpé en {len(chunks)} morceaux."
        )

        partial_summaries = [
            _summarize_chunk(pipeline_obj, c, max_length=120, min_length=30)
            for c in chunks
        ]
        current_text = " ".join(partial_summaries)
        pass_number += 1

        if pass_number > 15:
            logger.warning("Nombre de passes de réduction élevé, arrêt forcé.")
            return _summarize_chunk(pipeline_obj, current_text, max_length, min_length)