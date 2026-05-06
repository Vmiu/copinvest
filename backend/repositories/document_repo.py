from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import DocumentRecord


async def get_document_by_id(db: AsyncSession, document_id: str) -> DocumentRecord | None:
    result = await db.execute(
        select(DocumentRecord).where(DocumentRecord.document_id == document_id)
    )
    return result.scalar_one_or_none()


async def upsert_document_record(db: AsyncSession, record: DocumentRecord) -> DocumentRecord:
    existing = await get_document_by_id(db, record.document_id)
    if existing:
        existing.filename = record.filename
        existing.doc_type = record.doc_type
        existing.sensitivity_tier = record.sensitivity_tier
        existing.chunk_count = record.chunk_count
        existing.total_chars = record.total_chars
        existing.warnings = record.warnings
        existing.parse_duration_ms = record.parse_duration_ms
        existing.extraction_method = record.extraction_method
        existing.ingested_at = record.ingested_at
        existing.ingested_by = record.ingested_by
        await db.flush()
        return existing
    db.add(record)
    await db.flush()
    return record
