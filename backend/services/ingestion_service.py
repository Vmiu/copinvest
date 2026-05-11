import asyncio
import json
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import structlog
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import DocumentRecord
from backend.models.enums import SensitivityTier
from backend.repositories import document_repo, vector_repo
from backend.services import chunking_service, document_parser, embedding_service

logger = structlog.get_logger()

TIER_TO_ROLES: dict[int, list[str]] = {
    SensitivityTier.public: ["adviser", "senior_adviser", "admin"],
    SensitivityTier.internal: ["senior_adviser", "admin"],
    SensitivityTier.restricted: ["senior_adviser", "admin"],
    SensitivityTier.confidential: ["admin"],
}

DOC_TYPE_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
}


def _detect_doc_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    doc_type = DOC_TYPE_MAP.get(suffix)
    if not doc_type:
        raise ValueError(f"Unsupported file type: {suffix}")
    return doc_type


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
    document_type: str = "other",
    language: str = "en",
    jurisdiction: str = "global",
    product_codes: list[str] | None = None,
    parent_doc_title: str | None = None,
) -> dict:
    doc_id = document_id or str(uuid4())
    doc_type = _detect_doc_type(filename)
    warnings: list[str] = []
    start = time.monotonic()

    logger.info("ingestion_started", document_id=doc_id, filename=filename, doc_type=doc_type)

    # 1. Parse document (vision LLM for PDF, docling for everything else)
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(file_content)
        tmp.flush()
        if doc_type == "pdf":
            markdown = await document_parser.parse_pdf_vision(tmp.name, openrouter_client)
        else:
            markdown = await asyncio.to_thread(document_parser.parse_docling, tmp.name)

    if not markdown.strip():
        raise ValueError("Document parsed to empty content")

    # 2. LLM chunking (DeepSeek)
    chunks = await chunking_service.chunk_document(markdown, chunking_client)
    chunk_texts = [c["text"] for c in chunks]
    chunk_meta = [{k: v for k, v in c.items() if k != "text"} for c in chunks]

    # 3. Embed chunks (sentence-transformers, client param unused but kept for API compat)
    vectors = await embedding_service.embed_chunks(chunk_texts, openrouter_client)

    # 4. Upsert new chunks first (write-then-replace for atomicity — D-12)
    allowed_roles = TIER_TO_ROLES.get(sensitivity_tier.value, ["admin"])
    payload_base = {
        "source_id": doc_id,
        "doc_type": doc_type,
        "sensitivity_tier": sensitivity_tier.value,
        "allowed_roles": allowed_roles,
        "document_type": document_type,
        "language": language,
        "jurisdiction": jurisdiction,
        "product_codes": product_codes or [],
        "parent_doc_title": parent_doc_title or filename,
    }
    chunk_count, new_point_ids = vector_repo.upsert_chunks(
        qdrant_client, chunk_texts, vectors, payload_base, chunk_metadata=chunk_meta
    )

    # 4b. Only after new chunks are confirmed written, remove old ones
    vector_repo.delete_by_source_except_new(qdrant_client, doc_id, new_point_ids)

    # 5. Record in document registry (D-16)
    total_chars = sum(len(c) for c in chunk_texts)
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
        document_type=document_type,
        language=language,
        jurisdiction=jurisdiction,
        product_codes=json.dumps(product_codes) if product_codes else None,
        parent_doc_title=parent_doc_title or filename,
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
