from __future__ import annotations

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    logger.info("Loading sentence-transformer model: %s", _MODEL_NAME)
    return SentenceTransformer(_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Return a normalised embedding vector for the given text."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
