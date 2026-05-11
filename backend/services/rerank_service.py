import httpx
import structlog

from backend.core.config import get_settings

logger = structlog.get_logger()


async def rerank_chunks(
    query: str,
    chunks: list,
    threshold: float = 0.3,
    top_n: int = 5,
) -> list:
    """Return top_n chunks by their original retrieval order (no external reranker).

    Falls back to simple truncation since no rerank API is available locally.
    """
    if not chunks:
        return []
    return chunks[:top_n]
