from datetime import datetime, timezone, timedelta

import pytest

from backend.models.user import User
from backend.models.audit_log import Session as AuditSession
from backend.services.session_service import get_or_create_session


async def _seed_user(db):
    user = User(id="test-user", email="test@test.com",
                hashed_password="x", role="adviser")
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_create_session(db_session):
    await _seed_user(db_session)
    session_id = await get_or_create_session(db_session, "test-user")
    assert session_id
    assert isinstance(session_id, str)


@pytest.mark.asyncio
async def test_reuse_active_session(db_session):
    await _seed_user(db_session)
    sid1 = await get_or_create_session(db_session, "test-user")
    sid2 = await get_or_create_session(db_session, "test-user")
    assert sid1 == sid2


@pytest.mark.asyncio
async def test_expire_inactive_session(db_session):
    await _seed_user(db_session)
    sid1 = await get_or_create_session(db_session, "test-user")

    # Manually age the session beyond the 24h timeout
    from sqlalchemy import select
    result = await db_session.execute(
        select(AuditSession).where(AuditSession.id == sid1)
    )
    old_session = result.scalar_one()
    old_session.last_activity = datetime.now(timezone.utc) - timedelta(hours=25)
    await db_session.flush()

    sid2 = await get_or_create_session(db_session, "test-user")
    assert sid2 != sid1

    # Old session should have end_time set
    await db_session.refresh(old_session)
    assert old_session.end_time is not None
