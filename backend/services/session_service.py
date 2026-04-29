from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import Session as AuditSession

SESSION_TIMEOUT = timedelta(minutes=30)


async def get_or_create_session(db: AsyncSession, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    cutoff = now - SESSION_TIMEOUT
    # Find most recent open session for this user
    result = await db.execute(
        select(AuditSession)
        .where(AuditSession.user_id == user_id, AuditSession.end_time.is_(None))
        .order_by(AuditSession.start_time.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    # SQLite strips timezone info; normalize to naive UTC for comparison
    cutoff_naive = cutoff.replace(tzinfo=None)
    if session and session.start_time.replace(tzinfo=None) >= cutoff_naive:
        return session.id
    # Expire old session if exists
    if session:
        session.end_time = now
    # Create new session
    new_session = AuditSession(
        id=str(uuid4()), user_id=user_id, start_time=now,
    )
    db.add(new_session)
    await db.flush()
    return new_session.id
