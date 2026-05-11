import uuid
from pathlib import Path

import structlog
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.models.document import DocumentRecord
from backend.models.enums import SensitivityTier
from backend.repositories import document_repo, vector_repo
from backend.services import chunking_service, document_parser, embedding_service

logger = structlog.get_logger()

CHUNK_SIZE = 500      # characters
CHUNK_OVERLAP = 100

# Which roles can access each tier
TIER_ROLES: dict[str, list[str]] = {
    "internal": ["adviser", "senior_adviser", "compliance"],
    "restricted": ["senior_adviser", "compliance"],
}


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


async def ingest_document(
    db: AsyncSession,
    file_content: bytes,
    filename: str,
    sensitivity_tier: SensitivityTier,
    user_id: str,
    chunking_client: AsyncOpenAI,
    openrouter_client: AsyncOpenAI,
    qdrant_client: QdrantClient,
    document_id: str | None = None,
) -> dict:
    settings = get_settings()
    collection = collection or settings.qdrant_collection
    allowed_roles = TIER_ROLES[sensitivity_tier]
    tier_int = 2 if sensitivity_tier == "internal" else 3

    if ollama_client is None:
        ollama_client = OllamaClient(host=settings.ollama_base_url)

    # 1. Parse document (vision LLM for PDF, docling for everything else)
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp.flush()
        tmp_path = tmp.name
    try:
        if doc_type == "pdf":
            markdown = await document_parser.parse_pdf_vision(tmp_path, openrouter_client)
        else:
            markdown = await asyncio.to_thread(document_parser.parse_docling, tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    text = _extract_text(pdf_path)
    chunks = _chunk_text(text)

    # 2. LLM chunking (DeepSeek)
    chunks = await chunking_service.chunk_document(markdown, chunking_client)

    # 3. Embed chunks (sentence-transformers, client param unused but kept for API compat)
    vectors = await embedding_service.embed_chunks(chunks, openrouter_client)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "source": pdf_path.name,
                "sensitivity_tier": tier_int,
                "allowed_roles": allowed_roles,
                "chunk_index": idx,
                "text": chunk,
            },
        )
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings))
    ]

    qdrant.upsert(collection_name=collection, points=points)

    # 5. Record in document registry (D-16)
    total_chars = sum(len(c) for c in chunks)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    record = DocumentRecord(
        document_id=doc_id,
        filename=filename,
        doc_type=doc_type,
        sensitivity_tier=sensitivity_tier.value,
        chunk_count=chunk_count,
        total_chars=total_chars,
        warnings=json.dumps(warnings) if warnings else None,
        parse_duration_ms=elapsed_ms,
        extraction_method="vision_v1",
        ingested_by=user_id,
    )
    await document_repo.upsert_document_record(db, record)

    logger.info("ingestion_complete", document_id=doc_id, chunks=chunk_count, duration_ms=elapsed_ms)

    return {
        "document_id": doc_id,
        "filename": filename,
        "doc_type": doc_type,
        "sensitivity_tier": sensitivity_tier.value,
        "chunk_count": chunk_count,
        "total_chars": total_chars,
        "warnings": warnings,
        "parse_duration_ms": elapsed_ms,
        "extraction_method": "vision_v1",
    }
