import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()


async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=chunks,
    )
    vectors = [item.embedding for item in response.data]
    logger.info("embedding_complete", chunk_count=len(chunks), dimensions=len(vectors[0]) if vectors else 0)
    return vectors
