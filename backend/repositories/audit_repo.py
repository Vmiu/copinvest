from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog, Session
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


async def list_sessions(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            AuditLog.session_id,
            AuditLog.user_id,
            func.count(AuditLog.id).label("query_count"),
            func.min(AuditLog.timestamp).label("started_at"),
            func.max(AuditLog.timestamp).label("last_activity"),
        )
        .group_by(AuditLog.session_id, AuditLog.user_id)
        .order_by(func.max(AuditLog.timestamp).desc())
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt.offset(offset).limit(limit))).all()
    return [
        {
            "session_id": r.session_id,
            "user_id": r.user_id,
            "query_count": r.query_count,
            "started_at": r.started_at.isoformat(),
            "last_activity": r.last_activity.isoformat(),
        }
        for r in rows
    ], total


async def list_audits(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 25,
    user_id: str | None = None,
    session_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if session_id:
        stmt = stmt.where(AuditLog.session_id == session_id)
    if date_from:
        stmt = stmt.where(AuditLog.timestamp >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(AuditLog.timestamp <= datetime.fromisoformat(date_to))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total
