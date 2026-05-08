from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.models.enums import AdviserAction


async def get_audit_by_id(db: AsyncSession, trace_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == trace_id))
    return result.scalar_one_or_none()


async def get_audits_by_session(db: AsyncSession, session_id: str) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    return list(result.scalars().all())


async def update_adviser_action(
    db: AsyncSession,
    trace_id: str,
    action: str,
    final_response: str | None,
) -> None:
    audit = await get_audit_by_id(db, trace_id)
    if audit is None:
        raise ValueError(f"AuditLog {trace_id} not found")
    audit.adviser_action = AdviserAction(action)
    audit.adviser_edited = (action == "edited")
    audit.final_response = final_response
    await db.flush()
