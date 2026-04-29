from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog


async def get_audit_by_id(db: AsyncSession, trace_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == trace_id))
    return result.scalar_one_or_none()


async def get_audits_by_session(db: AsyncSession, session_id: str) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    return list(result.scalars().all())
