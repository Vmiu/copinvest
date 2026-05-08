"""TDD tests for 04-01: channel parameter on process_query and update_adviser_action in audit_repo."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from backend.models.user import User
from backend.models.audit_log import Session as AuditSession, AuditLog
from backend.models.enums import AdviserAction, AuditStatus


async def _seed_user_and_session(db):
    user = User(id="tele-user", email="tele@test.com", hashed_password="x", role="adviser")
    db.add(user)
    session = AuditSession(
        id="tele-session", user_id="tele-user", start_time=datetime.now(timezone.utc)
    )
    db.add(session)
    await db.flush()
    return user, session


# ---------------------------------------------------------------------------
# Tests for audit_repo.update_adviser_action
# ---------------------------------------------------------------------------

async def test_update_adviser_action_approved(db_session):
    """update_adviser_action('approved', None) sets adviser_action=approved, adviser_edited=False, final_response=None."""
    from backend.services.audit_service import create_audit_record
    from backend.repositories.audit_repo import update_adviser_action

    await _seed_user_and_session(db_session)
    audit = await create_audit_record(db_session, "tele-user", "query", "tele-session", "telegram")

    await update_adviser_action(db_session, audit.id, "approved", None)

    assert audit.adviser_action == AdviserAction.approved
    assert audit.adviser_edited is False
    assert audit.final_response is None


async def test_update_adviser_action_edited(db_session):
    """update_adviser_action('edited', 'revised text') sets adviser_action=edited, adviser_edited=True, final_response='revised text'."""
    from backend.services.audit_service import create_audit_record
    from backend.repositories.audit_repo import update_adviser_action

    await _seed_user_and_session(db_session)
    audit = await create_audit_record(db_session, "tele-user", "query", "tele-session", "telegram")

    await update_adviser_action(db_session, audit.id, "edited", "revised text")

    assert audit.adviser_action == AdviserAction.edited
    assert audit.adviser_edited is True
    assert audit.final_response == "revised text"


async def test_update_adviser_action_discarded(db_session):
    """update_adviser_action('discarded', None) sets adviser_action=discarded, adviser_edited=False, final_response=None."""
    from backend.services.audit_service import create_audit_record
    from backend.repositories.audit_repo import update_adviser_action

    await _seed_user_and_session(db_session)
    audit = await create_audit_record(db_session, "tele-user", "query", "tele-session", "telegram")

    await update_adviser_action(db_session, audit.id, "discarded", None)

    assert audit.adviser_action == AdviserAction.discarded
    assert audit.adviser_edited is False
    assert audit.final_response is None


async def test_update_adviser_action_unknown_trace_id(db_session):
    """update_adviser_action with unknown trace_id raises ValueError."""
    from backend.repositories.audit_repo import update_adviser_action

    with pytest.raises(ValueError, match="AuditLog nonexistent-id not found"):
        await update_adviser_action(db_session, "nonexistent-id", "approved", None)


async def test_update_adviser_action_uses_flush_not_commit(db_session):
    """update_adviser_action calls db.flush() not db.commit() — caller controls transaction."""
    from backend.services.audit_service import create_audit_record
    from backend.repositories.audit_repo import update_adviser_action

    await _seed_user_and_session(db_session)
    audit = await create_audit_record(db_session, "tele-user", "query", "tele-session", "telegram")

    # Wrap the session to spy on flush/commit calls
    original_flush = db_session.flush
    original_commit = db_session.commit
    flush_called = []
    commit_called = []

    async def spy_flush(*args, **kwargs):
        flush_called.append(True)
        return await original_flush(*args, **kwargs)

    async def spy_commit(*args, **kwargs):
        commit_called.append(True)
        return await original_commit(*args, **kwargs)

    db_session.flush = spy_flush
    db_session.commit = spy_commit

    await update_adviser_action(db_session, audit.id, "approved", None)

    db_session.flush = original_flush
    db_session.commit = original_commit

    assert len(flush_called) >= 1, "db.flush() should have been called"
    assert len(commit_called) == 0, "db.commit() must NOT be called — caller controls transaction"


# ---------------------------------------------------------------------------
# Tests for process_query channel parameter
# ---------------------------------------------------------------------------

async def test_process_query_channel_default_is_web(db_session):
    """process_query with no channel argument defaults to channel='web' in audit record."""
    from backend.services.query_service import process_query
    from sqlalchemy import select

    await _seed_user_and_session(db_session)

    mock_qdrant_result = MagicMock()
    mock_qdrant_result.points = []

    with (
        patch("backend.services.query_rewrite_service.rewrite_query", new_callable=AsyncMock, return_value="rewritten"),
        patch("backend.services.rerank_service.rerank_chunks", new_callable=AsyncMock, return_value=[]),
        patch("backend.services.generation_service.generate_answer", new_callable=AsyncMock, return_value={
            "answer": "answer",
            "sources": [],
            "not_found": False,
            "model_used": "test-model",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_sent": "prompt",
        }),
        patch("backend.repositories.vector_repo.query_with_rbac", return_value=mock_qdrant_result),
        patch("httpx.AsyncClient") as mock_http_cls,
    ):
        mock_http_instance = AsyncMock()
        mock_voyage_resp = MagicMock()
        mock_voyage_resp.raise_for_status = MagicMock()
        mock_voyage_resp.json.return_value = {"data": [{"embedding": [0.1] * 1024, "index": 0}]}
        mock_http_instance.post = AsyncMock(return_value=mock_voyage_resp)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await process_query(
            db=db_session,
            query="test query",
            session_id="tele-session",
            user_id="tele-user",
            user_role="adviser",
            chunking_client=MagicMock(),
            generation_client=MagicMock(),
            qdrant_client=MagicMock(),
            # no channel argument — should default to "web"
        )

    await db_session.commit()

    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.id == result["trace_id"])
    )
    audit = audit_result.scalar_one_or_none()
    assert audit is not None
    assert audit.channel == "web"


async def test_process_query_channel_telegram(db_session):
    """process_query with channel='telegram' records channel='telegram' in audit."""
    from backend.services.query_service import process_query
    from sqlalchemy import select

    await _seed_user_and_session(db_session)

    mock_qdrant_result = MagicMock()
    mock_qdrant_result.points = []

    with (
        patch("backend.services.query_rewrite_service.rewrite_query", new_callable=AsyncMock, return_value="rewritten"),
        patch("backend.services.rerank_service.rerank_chunks", new_callable=AsyncMock, return_value=[]),
        patch("backend.services.generation_service.generate_answer", new_callable=AsyncMock, return_value={
            "answer": "answer",
            "sources": [],
            "not_found": False,
            "model_used": "test-model",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_sent": "prompt",
        }),
        patch("backend.repositories.vector_repo.query_with_rbac", return_value=mock_qdrant_result),
        patch("httpx.AsyncClient") as mock_http_cls,
    ):
        mock_http_instance = AsyncMock()
        mock_voyage_resp = MagicMock()
        mock_voyage_resp.raise_for_status = MagicMock()
        mock_voyage_resp.json.return_value = {"data": [{"embedding": [0.1] * 1024, "index": 0}]}
        mock_http_instance.post = AsyncMock(return_value=mock_voyage_resp)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await process_query(
            db=db_session,
            query="test query",
            session_id="tele-session",
            user_id="tele-user",
            user_role="adviser",
            chunking_client=MagicMock(),
            generation_client=MagicMock(),
            qdrant_client=MagicMock(),
            channel="telegram",
        )

    await db_session.commit()

    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.id == result["trace_id"])
    )
    audit = audit_result.scalar_one_or_none()
    assert audit is not None
    assert audit.channel == "telegram"
