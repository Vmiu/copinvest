from datetime import datetime, timezone

from backend.models.user import User
from backend.models.audit_log import Session as AuditSession
from backend.models.enums import AuditStatus, AdviserAction
from backend.services.audit_service import (
    create_audit_record,
    update_retrieval,
    update_generation,
    update_adviser_action,
)
from backend.repositories.audit_repo import get_audit_by_id, get_audits_by_session


async def _seed_user_and_session(db):
    user = User(id="test-user", email="test@test.com",
                hashed_password="x", role="adviser")
    db.add(user)
    session = AuditSession(id="test-session", user_id="test-user",
                           start_time=datetime.now(timezone.utc))
    db.add(session)
    await db.flush()
    return user, session


async def test_create_audit_record(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, user_id="test-user", query_text="What is fund X?",
        session_id="test-session", channel="web",
    )
    assert audit.id is not None
    assert audit.status == AuditStatus.received
    assert audit.user_id == "test-user"
    assert audit.query_text == "What is fund X?"
    assert audit.session_id == "test-session"
    assert audit.channel == "web"
    assert audit.timestamp is not None


async def test_audit_progressive_lifecycle(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, "test-user", "query", "test-session", "web",
    )
    assert audit.status == AuditStatus.received

    await update_retrieval(db_session, audit, '["chunk1"]', 2, "prompt text")
    assert audit.status == AuditStatus.retrieved

    await update_generation(
        db_session, audit, "LLM says...", "gpt-4o-2024-11-20", 100, 50,
    )
    assert audit.status == AuditStatus.generated

    await update_adviser_action(
        db_session, audit, AdviserAction.approved, False,
    )
    assert audit.status == AuditStatus.completed


async def test_tier_recorded(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, "test-user", "query", "test-session", "web",
    )
    await update_retrieval(db_session, audit, '["chunk"]', 3, "prompt")
    assert audit.sensitivity_tier_accessed == 3


async def test_model_version_recorded(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, "test-user", "query", "test-session", "web",
    )
    await update_retrieval(db_session, audit, '["chunk"]', 1, "prompt")
    await update_generation(
        db_session, audit, "response", "gpt-4o-2024-11-20", 100, 50,
    )
    assert audit.model_used == "gpt-4o-2024-11-20"


async def test_adviser_action_recorded(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, "test-user", "query", "test-session", "web",
    )
    await update_adviser_action(
        db_session, audit, AdviserAction.approved, False,
    )
    assert audit.adviser_action == AdviserAction.approved


async def test_get_audit_by_id(db_session):
    await _seed_user_and_session(db_session)
    audit = await create_audit_record(
        db_session, "test-user", "query", "test-session", "web",
    )
    found = await get_audit_by_id(db_session, audit.id)
    assert found is not None
    assert found.id == audit.id


async def test_get_audits_by_session(db_session):
    await _seed_user_and_session(db_session)
    a1 = await create_audit_record(
        db_session, "test-user", "query 1", "test-session", "web",
    )
    a2 = await create_audit_record(
        db_session, "test-user", "query 2", "test-session", "web",
    )
    audits = await get_audits_by_session(db_session, "test-session")
    assert len(audits) == 2
    ids = {a.id for a in audits}
    assert a1.id in ids
    assert a2.id in ids
