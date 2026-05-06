import asyncio

import structlog
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()

# Loaded once at module import — kept in memory for the process lifetime
_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("embedding_model_loading", model=_MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    """Embed chunks locally using sentence-transformers (client param kept for API compat)."""
    if not chunks:
        raise ValueError("embed_chunks called with empty chunk list")
    model = _get_model()
    # SentenceTransformer.encode is CPU-bound — run in thread to avoid blocking event loop
    vectors = await asyncio.to_thread(
        lambda: model.encode(chunks, show_progress_bar=False).tolist()
    )
    logger.info("embedding_complete", chunk_count=len(chunks), dimensions=len(vectors[0]) if vectors else 0)
    return vectors
