import httpx
import structlog
from openai import AsyncOpenAI

from backend.core.config import get_settings

logger = structlog.get_logger()

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"


async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    """Embed chunks using Ollama nomic-embed-text."""
    if not chunks:
        raise ValueError("embed_chunks called with empty chunk list")

    settings = get_settings()
    vectors = []
    # Ollama /api/embed supports batch via list input
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            OLLAMA_EMBED_URL,
            json={"model": settings.embedding_model, "input": chunks},
        )
        resp.raise_for_status()

    vectors = resp.json()["embeddings"]
    logger.info(
        "embedding_complete",
        chunk_count=len(chunks),
        dimensions=len(vectors[0]) if vectors else 0,
    )
    return vectors
