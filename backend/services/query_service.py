import asyncio
import json

import httpx
import structlog
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.repositories.vector_repo import query_with_rbac
from backend.services import audit_service, generation_service, query_rewrite_service, rerank_service, session_service

logger = structlog.get_logger()

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"


async def process_query(
    db: AsyncSession,
    query: str,
    session_id: str | None,
    user_id: str,
    user_role: str,
    chunking_client: AsyncOpenAI,
    generation_client: AsyncOpenAI,
    qdrant_client: QdrantClient,
    channel: str = "web",
) -> dict:
    """Orchestrate the full RAG pipeline: session → audit → rewrite → embed → retrieve → rerank → generate → update audit."""

    # 1. Session
    session_id = await session_service.get_or_create_session(
        db, user_id, session_id=session_id
    )

    # 2. Audit record — commit immediately so it survives pipeline failures
    audit = await audit_service.create_audit_record(
        db, user_id, query, session_id, channel=channel
    )
    await db.commit()

    try:
        # 3. Query rewrite
        rewritten = await query_rewrite_service.rewrite_query(query, chunking_client)

        # 4. Embed query via Ollama
        settings = get_settings()
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                OLLAMA_EMBED_URL,
                json={
                    "model": settings.embedding_model,
                    "input": rewritten,
                },
            )
            resp.raise_for_status()
        query_vector = resp.json()["embeddings"][0]

        # 5. Retrieve from Qdrant (sync client wrapped in asyncio.to_thread)
        results = await asyncio.to_thread(
            query_with_rbac, qdrant_client, query_vector, user_role, limit=20
        )
        chunks = results.points

        # 6. Build retrieval audit data
        max_tier = max((pt.payload.get("sensitivity_tier", 0) for pt in chunks), default=0)
        retrieved_chunks_json = json.dumps([
            {
                "source_id": pt.payload.get("source_id"),
                "chunk_index": pt.payload.get("chunk_index"),
                "section_title": pt.payload.get("section_title"),
                "sensitivity_tier": pt.payload.get("sensitivity_tier"),
                "text": pt.payload.get("text"),
            }
            for pt in chunks
        ])

        # 7. Rerank — use original query (not rewritten) per D-06
        reranked = await rerank_service.rerank_chunks(
            query, chunks, threshold=0.3, top_n=5
        )

        # 8. Generate
        gen = await generation_service.generate_answer(rewritten, reranked, generation_client)

        # 6b. Update retrieval audit with actual prompt from generation
        await audit_service.update_retrieval(db, audit, retrieved_chunks_json, max_tier, gen["prompt_sent"])

        # 9. Update audit
        await audit_service.update_query_fields(
            db, audit, rewritten, len(reranked), gen["not_found"]
        )
        await audit_service.update_generation(
            db, audit, gen["answer"], gen["model_used"],
            gen["prompt_tokens"], gen["completion_tokens"],
        )

    except Exception as exc:
        await audit_service.update_error(db, audit, str(exc))
        await db.commit()
        raise

    logger.info(
        "query_pipeline_complete",
        trace_id=audit.id,
        not_found=gen["not_found"],
        chunks_retrieved=len(reranked),
    )

    # 10. Return
    return {
        "answer": gen["answer"],
        "sources": gen["sources"],
        "trace_id": audit.id,
        "session_id": session_id,
        "not_found": gen["not_found"],
        "chunks_retrieved": len(reranked),
        "model_used": gen["model_used"],
    }
