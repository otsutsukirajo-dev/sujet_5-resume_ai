import logging
from functools import lru_cache
from typing import List, Optional

logger = logging.getLogger(__name__)

# MODELE : plguillou/t5-base-fr-sum-cnndm est entraine NATIVEMENT en francais
# (fine-tune sur CNN/DailyMail traduit en francais), contrairement a
# facebook/bart-large-cnn qui est entraine uniquement en anglais et melange
# des mots anglais dans les resumes francais ("of", "It", "algorithm"...).
# Ce modele est de type T5 : il attend un prefixe "summarize: " devant le
# texte a resumer (voir MODEL_PROMPT_PREFIX plus bas).
DEFAULT_MODEL_NAME = "facebook/bart-large-cnn"
MODEL_PROMPT_PREFIX = ""  # requis par les modeles T5 (ex: "summarize: "). Vide pour bart-large-cnn.

MIN_CHUNK_TOKENS = 50
SAFETY_MARGIN = 20  # marge de sécurité en tokens sous la limite du modèle

# --- Paramètres de la longueur proportionnelle -----------------------------
# Le résumé final doit représenter environ SUMMARY_RATIO du texte source,
# borné par un plancher/plafond pour éviter les extrêmes (texte minuscule
# ou document énorme donnant un résumé ingérable).
SUMMARY_RATIO = 0.20          # ~20% du nombre de mots source
MIN_TARGET_WORDS = 150        # plancher : jamais un résumé plus court que ça
MAX_TARGET_WORDS = 1200       # plafond : jamais un résumé absurdement long
MIN_LENGTH_RATIO = 0.55       # min_length = ~55% du max_length calculé

# Pour les résumés PARTIELS (passes intermédiaires du map-reduce), on
# applique le même ratio à chaque chunk plutôt qu'une cible fixe, avec
# un plancher plus bas car un chunk individuel est plus petit que le
# document entier.
PARTIAL_MIN_TARGET_WORDS = 60
PARTIAL_MAX_TARGET_WORDS = 300

# CORRECTION MOTS -> TOKENS : max_length/min_length du pipeline HuggingFace
# sont exprimés en TOKENS, pas en mots. Pour un texte français, un tokenizer
# produit en général plus de tokens que de mots (subword splitting). On
# multiplie donc nos cibles "en mots" par ce facteur avant de les envoyer
# au pipeline, pour obtenir une longueur de sortie réellement proche de ce
# qui est demandé. Valeur prudente ajustable si les résumés restent trop
# courts/longs après tests.
TOKENS_PER_WORD_FACTOR = 1.4


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
        model_max = 1024  # valeur sûre par défaut
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


def _compute_target_length(word_count: int, floor: int, ceiling: int, ratio: float = SUMMARY_RATIO):
    """
    Calcule (max_length, min_length) EN MOTS, proportionnels au nombre de
    mots d'un texte, bornés par [floor, ceiling]. La conversion en tokens
    (pour le pipeline) se fait séparément via TOKENS_PER_WORD_FACTOR.
    """
    target_max = int(word_count * ratio)
    target_max = max(floor, min(ceiling, target_max))
    target_min = max(1, int(target_max * MIN_LENGTH_RATIO))
    if target_min >= target_max:
        target_min = max(1, target_max - 1)
    return target_max, target_min


def _summarize_chunk(pipeline_obj, chunk: str, max_length_words: int, min_length_words: int) -> str:
    word_count = len(chunk.split())

    # Conversion mots -> tokens pour le pipeline (voir TOKENS_PER_WORD_FACTOR).
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
        raise SummarizationError(f"Erreur pendant la génération du résumé : {e}")


def summarize_text(
    text: str,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """
    Génère un résumé, quelle que soit la longueur du texte source.
    Utilise une réduction récursive (map-reduce) : le document est
    découpé, chaque morceau est résumé, les résumés sont recombinés,
    et on recommence tant que le résultat ne tient pas en un seul bloc.

    La longueur cible du résumé FINAL est proportionnelle au nombre de
    mots du texte source (voir SUMMARY_RATIO), sauf si max_length/
    min_length sont fournis explicitement par l'appelant.

    Les résumés PARTIELS (passes intermédiaires) suivent le même
    principe : chaque chunk est résumé proportionnellement à sa propre
    taille, au lieu d'une cible fixe identique pour tous.
    """
    if not text or not text.strip():
        raise SummarizationError("Le texte à résumer est vide.")

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
        f"Document de {original_word_count} mots -> cible de résumé final : "
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
            logger.info(f"Résumé final généré en {pass_number} passe(s).")
            return _summarize_chunk(pipeline_obj, chunks[0], final_max_length, final_min_length)

        logger.info(
            f"Passe {pass_number} : document découpé en {len(chunks)} morceaux."
        )

        partial_summaries = []
        for c in chunks:
            chunk_word_count = len(c.split())
            chunk_max, chunk_min = _compute_target_length(
                chunk_word_count, PARTIAL_MIN_TARGET_WORDS, PARTIAL_MAX_TARGET_WORDS
            )
            partial_summaries.append(
                _summarize_chunk(pipeline_obj, c, chunk_max, chunk_min)
            )

        current_text = " ".join(partial_summaries)
        pass_number += 1

        if pass_number > 15:
            logger.warning("Nombre de passes de réduction élevé, arrêt forcé.")
            return _summarize_chunk(pipeline_obj, current_text, final_max_length, final_min_length)
