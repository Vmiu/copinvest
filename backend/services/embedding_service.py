import httpx
import structlog
from openai import AsyncOpenAI

from backend.core.config import get_settings

logger = structlog.get_logger()

VOYAGE_MODEL = "voyage-finance-2"
VOYAGE_EMBED_URL = "https://api.voyageai.com/v1/embeddings"
EMBEDDING_DIMENSIONS = 1024


async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    """Embed chunks using Voyage AI (client param kept for API compat, unused)."""
    if not chunks:
        raise ValueError("embed_chunks called with empty chunk list")

    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(
            VOYAGE_EMBED_URL,
            headers={
                "Authorization": f"Bearer {settings.voyage_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VOYAGE_MODEL,
                "input": chunks,
                "input_type": "document",
            },
        )
        resp.raise_for_status()

    data = resp.json()
    vectors = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
    logger.info(
        "embedding_complete",
        chunk_count=len(chunks),
        dimensions=len(vectors[0]) if vectors else 0,
        tokens_used=data.get("usage", {}).get("total_tokens"),
    )
    return vectors
