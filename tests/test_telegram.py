"""Tests for Phase 4: Telegram Bot — audit write-back, channel parameter, and bot handlers."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models.user import User
from backend.models.audit_log import AuditLog, Session as AuditSession
from backend.models.enums import AdviserAction, AuditStatus
from backend.repositories import audit_repo
from backend.services import audit_service


# ── Seed helpers ──────────────────────────────────────────────────────────────

async def _seed_user_and_session(db, user_id="test-user", session_id="test-session"):
    user = User(id=user_id, email="test@test.com", hashed_password="x", role="adviser")
    db.add(user)
    session = AuditSession(
        id=session_id, user_id=user_id,
        start_time=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    return user, session


async def _seed_audit(db, trace_id="test-trace-001", llm_response=None):
    """Create a minimal AuditLog row for testing."""
    await _seed_user_and_session(db)
    audit = await audit_service.create_audit_record(
        db, user_id="test-user", query_text="What is fund X?",
        session_id="test-session", channel="telegram",
    )
    # Override the auto-generated id with the requested trace_id
    audit.id = trace_id
    if llm_response is not None:
        audit.llm_response = llm_response
    await db.flush()
    return audit


# ── audit_repo.update_adviser_action ─────────────────────────────────────────

async def test_update_adviser_action_approve(db_session):
    await _seed_audit(db_session, trace_id="trace-approve", llm_response="test answer")
    await audit_repo.update_adviser_action(db_session, "trace-approve", "approved", "test answer")
    audit = await audit_repo.get_audit_by_id(db_session, "trace-approve")
    assert audit.adviser_action == AdviserAction.approved
    assert audit.adviser_edited is False
    assert audit.final_response == "test answer"


async def test_update_adviser_action_edited(db_session):
    await _seed_audit(db_session, trace_id="trace-edited")
    await audit_repo.update_adviser_action(db_session, "trace-edited", "edited", "revised text")
    audit = await audit_repo.get_audit_by_id(db_session, "trace-edited")
    assert audit.adviser_action == AdviserAction.edited
    assert audit.adviser_edited is True
    assert audit.final_response == "revised text"


async def test_update_adviser_action_discard(db_session):
    await _seed_audit(db_session, trace_id="trace-discard")
    await audit_repo.update_adviser_action(db_session, "trace-discard", "discarded", None)
    audit = await audit_repo.get_audit_by_id(db_session, "trace-discard")
    assert audit.adviser_action == AdviserAction.discarded
    assert audit.adviser_edited is False


async def test_update_adviser_action_unknown_trace_id(db_session):
    with pytest.raises(ValueError):
        await audit_repo.update_adviser_action(db_session, "nonexistent-id", "approved", None)


async def test_update_adviser_action_uses_flush_not_commit(db_session):
    await _seed_audit(db_session, trace_id="trace-flush")
    await audit_repo.update_adviser_action(db_session, "trace-flush", "approved", "answer")
    # flush() does not commit — session should still be in a transaction
    assert db_session.in_transaction()


# ── Telegram handler test helpers ─────────────────────────────────────────────

def make_update(text: str, user_id: int = 12345):
    user = MagicMock()
    user.id = user_id
    user.is_bot = False
    message = MagicMock()
    message.text = text
    message.from_user = user
    message.reply_text = AsyncMock()
    message.chat = MagicMock()
    message.chat.send_action = AsyncMock()
    update = MagicMock()
    update.message = message
    update.effective_user = user
    return update


def make_context(user_data=None, bot_data=None):
    context = MagicMock()
    context.user_data = user_data or {}
    context.bot_data = bot_data or {
        "chunking_client": MagicMock(),
        "generation_client": MagicMock(),
        "qdrant_client": MagicMock(),
    }
    return context


def make_callback_update(data: str, user_id: int = 12345):
    query = MagicMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    return update


def _make_mock_session():
    """Return a mock async_session context manager."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_session_cm, mock_db


# ── handle_query tests ────────────────────────────────────────────────────────

async def test_handle_query_unregistered_user():
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_query

    update = make_update("What is fund X?", user_id=99999)
    context = make_context()

    with patch("backend.telegram_bot.handlers.get_user_from_telegram_id", return_value=None):
        result = await handle_query(update, context)

    update.message.reply_text.assert_called_once_with(
        "Your Telegram account is not registered. Contact your administrator."
    )
    assert result == ConversationHandler.END


async def test_handle_query_sends_draft_with_keyboard():
    from telegram import InlineKeyboardMarkup
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_query

    update = make_update("What is fund X?")
    context = make_context()
    mock_session_cm, mock_db = _make_mock_session()

    fake_user = {"user_id": "u-001", "role": "adviser"}
    fake_result = {"answer": "test answer", "sources": [{"doc_name": "Doc A", "section_title": ""}], "trace_id": "t-001", "session_id": "s-001"}

    with patch("backend.telegram_bot.handlers.get_user_from_telegram_id", return_value=fake_user), \
         patch("backend.telegram_bot.handlers.process_query", new=AsyncMock(return_value=fake_result)), \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        result = await handle_query(update, context)

    assert result == ConversationHandler.END
    call_args = update.message.reply_text.call_args
    assert call_args is not None
    reply_markup = call_args.kwargs.get("reply_markup") or (call_args.args[1] if len(call_args.args) > 1 else None)
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    assert len(reply_markup.inline_keyboard[0]) == 3


async def test_handle_query_stores_trace_id():
    from backend.telegram_bot.handlers import handle_query

    update = make_update("What is fund X?")
    context = make_context()
    mock_session_cm, mock_db = _make_mock_session()

    fake_user = {"user_id": "u-001", "role": "adviser"}
    fake_result = {"answer": "test answer", "sources": [], "trace_id": "t-001", "session_id": "s-001"}

    with patch("backend.telegram_bot.handlers.get_user_from_telegram_id", return_value=fake_user), \
         patch("backend.telegram_bot.handlers.process_query", new=AsyncMock(return_value=fake_result)), \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        await handle_query(update, context)

    assert context.user_data["trace_id"] == "t-001"


async def test_handle_query_pipeline_error():
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_query

    update = make_update("What is fund X?")
    context = make_context()
    mock_session_cm, mock_db = _make_mock_session()

    fake_user = {"user_id": "u-001", "role": "adviser"}

    with patch("backend.telegram_bot.handlers.get_user_from_telegram_id", return_value=fake_user), \
         patch("backend.telegram_bot.handlers.process_query", new=AsyncMock(side_effect=RuntimeError("pipeline failed"))), \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        result = await handle_query(update, context)

    update.message.reply_text.assert_called_once_with("Something went wrong — please try again.")
    assert result == ConversationHandler.END


# ── handle_action tests ───────────────────────────────────────────────────────

async def test_handle_action_approve():
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_action

    update = make_callback_update("approve")
    context = make_context(user_data={"trace_id": "t-approve"})
    mock_session_cm, mock_db = _make_mock_session()

    fake_audit = MagicMock()
    fake_audit.llm_response = "original answer"

    with patch("backend.telegram_bot.handlers.audit_repo.get_audit_by_id", new=AsyncMock(return_value=fake_audit)), \
         patch("backend.telegram_bot.handlers.audit_repo.update_adviser_action", new=AsyncMock()) as mock_update, \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        result = await handle_action(update, context)

    mock_update.assert_called_once_with(mock_db, "t-approve", "approved", "original answer")
    assert result == ConversationHandler.END


async def test_handle_action_edit_returns_awaiting():
    from backend.telegram_bot.handlers import handle_action, AWAITING_EDIT

    update = make_callback_update("edit")
    context = make_context(user_data={"trace_id": "t-edit"})

    result = await handle_action(update, context)

    assert result == AWAITING_EDIT
    update.callback_query.message.reply_text.assert_called_once_with("Send your revised version:")


async def test_handle_action_discard():
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_action

    update = make_callback_update("discard")
    context = make_context(user_data={"trace_id": "t-discard"})
    mock_session_cm, mock_db = _make_mock_session()

    with patch("backend.telegram_bot.handlers.audit_repo.update_adviser_action", new=AsyncMock()) as mock_update, \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        result = await handle_action(update, context)

    mock_update.assert_called_once_with(mock_db, "t-discard", "discarded", None)
    assert result == ConversationHandler.END


async def test_handle_edit_reply():
    from telegram.ext import ConversationHandler
    from backend.telegram_bot.handlers import handle_edit_reply

    update = make_update("replacement text")
    context = make_context(user_data={"trace_id": "t-edit-reply"})
    mock_session_cm, mock_db = _make_mock_session()

    with patch("backend.telegram_bot.handlers.audit_repo.update_adviser_action", new=AsyncMock()) as mock_update, \
         patch("backend.telegram_bot.handlers.async_session", return_value=mock_session_cm):
        result = await handle_edit_reply(update, context)

    mock_update.assert_called_once_with(mock_db, "t-edit-reply", "edited", "replacement text")
    update.message.reply_text.assert_called_once_with("Revised response recorded.")
    assert result == ConversationHandler.END


async def test_bot_main_raises_on_empty_token():
    with patch("backend.telegram_bot.bot.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.telegram_bot_token = ""
        mock_get_settings.return_value = mock_settings
        from backend.telegram_bot.bot import main
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            main()
