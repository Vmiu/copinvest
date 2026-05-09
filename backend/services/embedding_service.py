import asyncio

import httpx
import structlog
from openai import AsyncOpenAI

from backend.core.config import get_settings

logger = structlog.get_logger()

VOYAGE_MODEL = "voyage-finance-2"
VOYAGE_EMBED_URL = "https://api.voyageai.com/v1/embeddings"
EMBEDDING_DIMENSIONS = 1024
_BATCH_SIZE = 10
_BATCH_DELAY = 2.0  # seconds between batches — stays within Voyage free-tier RPM


async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    """Embed chunks using Voyage AI in batches to respect rate limits."""
    if not chunks:
        raise ValueError("embed_chunks called with empty chunk list")

    settings = get_settings()
    all_vectors: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60) as http:
        for i in range(0, len(chunks), _BATCH_SIZE):
            batch = chunks[i: i + _BATCH_SIZE]
            if i > 0:
                await asyncio.sleep(_BATCH_DELAY)
            resp = await http.post(
                VOYAGE_EMBED_URL,
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": VOYAGE_MODEL,
                    "input": batch,
                    "input_type": "document",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            batch_vectors = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            all_vectors.extend(batch_vectors)
            logger.info(
                "embedding_batch_complete",
                batch=i // _BATCH_SIZE + 1,
                batch_size=len(batch),
                total_so_far=len(all_vectors),
            )

    logger.info(
        "embedding_complete",
        chunk_count=len(chunks),
        dimensions=len(all_vectors[0]) if all_vectors else 0,
    )
    return all_vectors
