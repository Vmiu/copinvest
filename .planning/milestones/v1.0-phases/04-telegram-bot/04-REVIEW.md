---
phase: 04-telegram-bot
reviewed: 2026-05-09T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - backend/core/config.py
  - backend/repositories/audit_repo.py
  - backend/services/query_service.py
  - backend/telegram_bot/__init__.py
  - backend/telegram_bot/__main__.py
  - backend/telegram_bot/bot.py
  - backend/telegram_bot/handlers.py
  - backend/telegram_bot/identity.py
  - pyproject.toml
  - tests/test_telegram.py
findings:
  critical: 3
  warning: 4
  info: 2
  total: 9
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-09T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 4 adds a Telegram bot channel to the existing RAG pipeline. The core plumbing (identity lookup, audit write-back, inline keyboard flow) is structurally sound. However, there are three blockers: a broken `ConversationHandler` state transition caused by registering `handle_action` outside the conversation, a `session_id` that is never actually persisted back to `context.user_data` (so every message starts a new session), and a missing `json.JSONDecodeError` guard in `identity.py` that will crash the bot on a misconfigured env var. Four warnings cover an unvalidated role value that bypasses RBAC, a `process_query` result dict that never includes `session_id`, an unguarded `update.effective_user` dereference, and a missing `httpx` production dependency. Two info items cover a magic number and a missing `pytest-asyncio` marker.

---

## Critical Issues

### CR-01: `handle_action` registered outside `ConversationHandler` — Edit flow state transition is broken

**File:** `backend/telegram_bot/bot.py:41-51`

**Issue:** `handle_action` is added as a standalone `CallbackQueryHandler` (line 41) *before* the `ConversationHandler` is registered. In python-telegram-bot, a standalone handler at the application level runs independently of any conversation state. When `handle_action` returns `AWAITING_EDIT` (integer `1`), that return value is ignored — the `ConversationHandler` never sees it and the conversation state is never set to `AWAITING_EDIT`. As a result, when the user sends their edited text, `handle_edit_reply` is never invoked; the message falls through to `handle_query` instead, triggering a second RAG pipeline call with the adviser's replacement text as a new query.

The correct pattern is to register `handle_action` *inside* the `ConversationHandler` as a `CallbackQueryHandler` entry in both the top-level `entry_points` (or as a state handler) and in the `AWAITING_EDIT` state, so the conversation framework can track the state transition.

**Fix:**
```python
conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query),
        CallbackQueryHandler(handle_action),  # handles approve/discard/edit at top level
    ],
    states={
        AWAITING_EDIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_reply),
            CallbackQueryHandler(handle_action),  # allow re-action while awaiting edit
        ]
    },
    fallbacks=[],
    per_user=True,
    per_chat=True,
    per_message=False,
    conversation_timeout=300,
)
# Remove the standalone: app.add_handler(CallbackQueryHandler(handle_action))
```

---

### CR-02: `session_id` is never returned by `process_query` — every Telegram message starts a new session

**File:** `backend/telegram_bot/handlers.py:59` and `backend/services/query_service.py:114-122`

**Issue:** `handle_query` attempts to persist the session for continuity:
```python
context.user_data["session_id"] = result.get("session_id", session_id)
```
But `process_query` never includes `session_id` in its return dict (lines 114-122 of `query_service.py`). `result.get("session_id", session_id)` always falls back to the *old* `session_id` from `context.user_data`, which is `None` on the first message. On every subsequent message, `session_id` is still `None`, so `session_service.get_or_create_session` creates a new session for every query. The audit trail is fragmented — each message appears as an isolated session rather than a conversation thread.

**Fix — add `session_id` to the return dict in `query_service.py`:**
```python
    return {
        "answer": gen["answer"],
        "sources": gen["sources"],
        "trace_id": audit.id,
        "session_id": session_id,   # <-- add this
        "not_found": gen["not_found"],
        "chunks_retrieved": len(reranked),
        "model_used": gen["model_used"],
    }
```

---

### CR-03: `json.loads` in `identity.py` raises unhandled `JSONDecodeError` — crashes the bot on misconfigured env

**File:** `backend/telegram_bot/identity.py:9`

**Issue:** `json.loads(settings.telegram_user_map)` will raise `json.JSONDecodeError` if `TELEGRAM_USER_MAP` is set to a malformed value in the environment (e.g., a single-quoted string, trailing comma, or accidentally set to a non-JSON value). This exception propagates uncaught through `handle_query`, bypasses the `try/except` block (the identity check runs before it), and surfaces as an unhandled exception in the Telegram dispatcher — causing the bot to silently drop the message with no user-facing error. Because `get_settings()` is cached via `@lru_cache`, a bad value at startup will permanently break identity resolution for all users until the process is restarted.

**Fix — validate at startup in `bot.py` and guard in `identity.py`:**
```python
# identity.py
def get_user_from_telegram_id(telegram_user_id: int) -> dict | None:
    settings = get_settings()
    try:
        user_map = json.loads(settings.telegram_user_map)
    except json.JSONDecodeError:
        logger.error("telegram_user_map_invalid_json")
        return None
    return user_map.get(str(telegram_user_id))
```

---

## Warnings

### WR-01: Role value from `telegram_user_map` is never validated — arbitrary string bypasses RBAC tier logic

**File:** `backend/telegram_bot/identity.py:6-10` and `backend/telegram_bot/handlers.py:44`

**Issue:** The `role` field read from `telegram_user_map` is passed directly to `process_query` as `user_role` without validation against `UserRole` enum values. In `vector_repo.query_with_rbac`, the role string is used in a Qdrant `MatchValue` filter. An invalid role (e.g., `"admin"`, `"superuser"`, or an empty string) will not match any sensitivity tier and will silently return zero results — or, depending on the Qdrant filter logic, could match unintended documents. A misconfigured `telegram_user_map` entry can therefore either deny all access or grant unintended access without any error.

**Fix:**
```python
# identity.py — validate role before returning
from backend.models.enums import UserRole

def get_user_from_telegram_id(telegram_user_id: int) -> dict | None:
    ...
    entry = user_map.get(str(telegram_user_id))
    if entry is None:
        return None
    role = entry.get("role", "")
    if role not in {r.value for r in UserRole}:
        logger.warning("telegram_user_invalid_role", role=role)
        return None
    return entry
```

---

### WR-02: `update.effective_user` is not guarded against `None` — crashes on channel posts

**File:** `backend/telegram_bot/handlers.py:17`

**Issue:** `update.effective_user.id` is accessed without a None check. In Telegram, `effective_user` is `None` for channel posts and certain service messages. If the bot is added to a channel or receives a forwarded channel message, this line raises `AttributeError`, which propagates as an unhandled exception. The `ConversationHandler` will log the error and drop the update silently.

**Fix:**
```python
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user is None:
        return ConversationHandler.END
    telegram_user_id = update.effective_user.id
    ...
```

---

### WR-03: `httpx` is a production dependency used in `query_service.py` but listed only under `[dev]`

**File:** `pyproject.toml:28`

**Issue:** `httpx>=0.28.0` appears only in `[project.optional-dependencies] dev`. However, `backend/services/query_service.py` imports and uses `httpx.AsyncClient` at line 49 for the Voyage embedding API call — this is a core production code path, not a test-only dependency. A production deployment that installs only `pip install copinvest` (without `[dev]`) will fail at runtime with `ModuleNotFoundError: No module named 'httpx'` on the first query.

**Fix — move `httpx` to the main `[project] dependencies` list:**
```toml
dependencies = [
    ...
    "httpx>=0.28.0",
    ...
]
```
And remove it from `[project.optional-dependencies] dev`.

---

### WR-04: `handle_action` opens two separate DB sessions for `approve` — TOCTOU window and double session overhead

**File:** `backend/telegram_bot/handlers.py:99-114`

**Issue:** For the `approve` action, the handler opens one `async_session()` to fetch `audit_row.llm_response` (lines 100-103), closes it, then opens a second `async_session()` to call `update_adviser_action` (lines 112-115). Between the two sessions, another process could theoretically modify the audit row. More practically, this is unnecessary overhead — `update_adviser_action` in `audit_repo.py` already fetches the audit row internally via `get_audit_by_id`. The `llm_response` could be read in the same session as the update.

**Fix — consolidate into a single session:**
```python
if action == "approve":
    audit_action = "approved"
    confirm_text = "Response approved and recorded."
    if trace_id:
        async with async_session() as db:
            audit_row = await audit_repo.get_audit_by_id(db, trace_id)
            final_response = audit_row.llm_response if audit_row else None
            await audit_repo.update_adviser_action(db, trace_id, audit_action, final_response)
            await db.commit()
    await callback.message.reply_text(confirm_text)
    return ConversationHandler.END
```

---

## Info

### IN-01: Magic number `AWAITING_EDIT = 1` should use `ConversationHandler` constant

**File:** `backend/telegram_bot/handlers.py:12`

**Issue:** `AWAITING_EDIT = 1` is a bare integer. If additional conversation states are added later, maintaining correct integer values manually is error-prone. The conventional pattern is to use an `IntEnum` or define states as a named constant block.

**Fix:**
```python
import enum

class State(enum.IntEnum):
    AWAITING_EDIT = 1
```
Or simply document the value clearly and keep it co-located with the `ConversationHandler` definition in `bot.py` rather than in `handlers.py`.

---

### IN-02: Test file lacks `@pytest.mark.asyncio` markers — relies on global `asyncio_mode = "auto"`

**File:** `tests/test_telegram.py` (all async test functions)

**Issue:** All async test functions rely on `asyncio_mode = "auto"` in `pyproject.toml` to run without explicit markers. This is functional but fragile — if `asyncio_mode` is ever changed or a test is moved to a file with a different config, the tests will silently become no-ops (collected but not awaited). Explicit `@pytest.mark.asyncio` markers make intent clear and are resilient to config changes.

**Fix:** Add `@pytest.mark.asyncio` to each async test function, or add a module-level marker:
```python
pytestmark = pytest.mark.asyncio
```

---

_Reviewed: 2026-05-09T00:00:00Z_
_Reviewer: Kiro (gsd-code-reviewer)_
_Depth: standard_
