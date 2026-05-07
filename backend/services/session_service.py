from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import Session as AuditSession

SESSION_TIMEOUT = timedelta(hours=24)


async def get_or_create_session(
    db: AsyncSession, user_id: str, session_id: str | None = None
) -> str:
    now = datetime.now(timezone.utc)
    cutoff = now - SESSION_TIMEOUT

    if session_id is not None:
        # Caller supplied a session_id — look it up directly
        result = await db.execute(
            select(AuditSession).where(AuditSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        # Ownership check — treat mismatched session as not found
        if session and session.user_id != user_id:
            session = None
        if session and session.end_time is None:
            activity_time = session.last_activity or session.start_time
            # Ensure timezone-aware comparison
            if activity_time.tzinfo is None:
                activity_time = activity_time.replace(tzinfo=timezone.utc)
            if activity_time >= cutoff:
                session.last_activity = now
                await db.flush()
                return session.id
        # Session not found, expired, or closed — fall through to create new
    else:
        # No session_id supplied — find most recent open session for this user
        result = await db.execute(
            select(AuditSession)
            .where(AuditSession.user_id == user_id, AuditSession.end_time.is_(None))
            .order_by(AuditSession.start_time.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session:
            activity_time = session.last_activity or session.start_time
            # Ensure timezone-aware comparison
            if activity_time.tzinfo is None:
                activity_time = activity_time.replace(tzinfo=timezone.utc)
            if activity_time >= cutoff:
                session.last_activity = now
                await db.flush()
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
