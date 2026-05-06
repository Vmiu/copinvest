from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class DocumentRecord(Base):
    __tablename__ = "document_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(50))
    sensitivity_tier: Mapped[int] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer)
    total_chars: Mapped[int] = mapped_column(Integer)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_duration_ms: Mapped[int] = mapped_column(Integer)
    extraction_method: Mapped[str] = mapped_column(String(100))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    ingested_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
