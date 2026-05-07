import httpx
import structlog

logger = structlog.get_logger()

RERANK_URL = "https://openrouter.ai/api/v1/rerank"
RERANK_MODEL = "cohere/rerank-v3.5"


async def rerank_chunks(
    query: str,
    chunks: list,
    api_key: str,
    threshold: float = 0.3,
    top_n: int = 5,
) -> list:
    """Rerank chunks via OpenRouter cohere/rerank-v3.5.

    chunks: list of ScoredPoint from Qdrant.
    Returns top_n ScoredPoints that pass the threshold, ordered by relevance_score desc.
    Falls back to top top_n by original Qdrant score on httpx error.
    """
    if not chunks:
        return []

    documents = [pt.payload["text"] for pt in chunks]

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                RERANK_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": RERANK_MODEL,
                    "query": query,
                    "documents": documents,
                    "top_n": len(chunks),
                },
            )
            resp.raise_for_status()

        results = resp.json()["results"]  # [{index, relevance_score}, ...]
        # Filter to threshold, sort by relevance_score desc, take top_n
        passing = [r for r in results if r["relevance_score"] >= threshold]
        passing.sort(key=lambda r: r["relevance_score"], reverse=True)
        reranked = [chunks[r["index"]] for r in passing[:top_n]]

        logger.info(
            "rerank_complete",
            input_count=len(chunks),
            passed_count=len(passing),
            returned_count=len(reranked),
        )
        return reranked

    except httpx.HTTPError as e:
        logger.warning("rerank_fallback", error=str(e))
        return chunks[:top_n]
