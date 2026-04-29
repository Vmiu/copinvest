from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.models.enums import AuditStatus, AdviserAction


async def create_audit_record(
    db: AsyncSession, user_id: str, query_text: str,
    session_id: str, channel: str,
) -> AuditLog:
    audit = AuditLog(
        id=str(uuid4()), user_id=user_id, query_text=query_text,
        session_id=session_id, channel=channel,
        timestamp=datetime.now(timezone.utc), status=AuditStatus.received,
    )
    db.add(audit)
    await db.flush()
    return audit


async def update_retrieval(
    db: AsyncSession, audit: AuditLog,
    chunks_json: str, max_tier: int, prompt: str,
) -> None:
    audit.retrieved_chunks = chunks_json
    audit.sensitivity_tier_accessed = max_tier
    audit.prompt_sent = prompt
    audit.status = AuditStatus.retrieved
    await db.flush()


async def update_generation(
    db: AsyncSession, audit: AuditLog,
    llm_response: str, model_used: str,
    prompt_tokens: int, completion_tokens: int,
) -> None:
    audit.llm_response = llm_response
    audit.model_used = model_used
    audit.prompt_tokens = prompt_tokens
    audit.completion_tokens = completion_tokens
    audit.status = AuditStatus.generated
    await db.flush()


async def update_adviser_action(
    db: AsyncSession, audit: AuditLog,
    action: AdviserAction, edited: bool,
    final_response: str | None = None,
) -> None:
    audit.adviser_action = action
    audit.adviser_edited = edited
    audit.final_response = final_response
    audit.status = AuditStatus.completed
    await db.flush()
