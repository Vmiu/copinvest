from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.enums import AdviserAction, AuditStatus


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String)
    query_text: Mapped[str] = mapped_column(Text)
    status: Mapped[AuditStatus] = mapped_column(SAEnum(AuditStatus))
    # Updated after retrieval
    retrieved_chunks: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_tier_accessed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_sent: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Updated after LLM response
    llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Updated after adviser action
    adviser_action: Mapped[AdviserAction | None] = mapped_column(SAEnum(AdviserAction), nullable=True)
    adviser_edited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Added for query pipeline (Phase 3)
    rewritten_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunks_passed_rerank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    not_found: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
