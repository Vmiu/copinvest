# Phase 4: Telegram Bot — Research

**Phase:** 4 — Telegram Bot
**Researched:** 2026-05-09
**Status:** Complete

---

## 1. python-telegram-bot 22.x ConversationHandler Pattern

### Application Bootstrap

```python
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

async def main():
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(conv_handler)
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

`Application.run_polling()` is a coroutine in v22.x — wrap in `asyncio.run()`. It manages its own event loop internally; do NOT call it from within an existing running loop (e.g., FastAPI's). The bot runs as a **separate process** (`uv run python -m backend.telegram_bot`), which is the correct isolation pattern.

### ConversationHandler for Edit Wait State

```python
AWAITING_EDIT = 1  # State constant

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query)],
    states={
        AWAITING_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_reply)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True,   # default — each user has independent state
    per_chat=True,   # default
)
```

`user_data` dict persists across handler calls within a conversation. Store `trace_id` there:

```python
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await process_query(...)
    context.user_data["trace_id"] = result["trace_id"]
    context.user_data["session_id"] = session_id
    # send draft with inline keyboard
    return ConversationHandler.END  # or AWAITING_EDIT if edit pressed
```

### Inline Keyboard and Callback Query

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✓ Approve", callback_data="approve"),
        InlineKeyboardButton("✏ Edit", callback_data="edit"),
        InlineKeyboardButton("✗ Discard", callback_data="discard"),
    ]
])
await update.message.reply_text(draft_text, reply_markup=keyboard)
```

**Callback query handler** — must answer the callback to remove the loading spinner, then edit the message to remove the keyboard:

```python
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # REQUIRED — removes Telegram's loading spinner
    action = query.data  # "approve" | "edit" | "discard"
    
    # Remove inline keyboard from original message
    await query.edit_message_reply_markup(reply_markup=None)
    
    if action == "edit":
        await query.message.reply_text("Send your revised version:")
        return AWAITING_EDIT  # transition to edit wait state
    
    # handle approve/discard inline
    ...
    return ConversationHandler.END
```

**Important:** `CallbackQueryHandler` must be in the `states` dict for the state where the keyboard is shown, AND in `entry_points` if the keyboard appears before any state transition. For this phase, the keyboard appears immediately after the query response — put `CallbackQueryHandler(handle_action)` in `entry_points` (or as a top-level handler outside ConversationHandler if the conversation only activates on Edit).

**Simpler architecture:** Use ConversationHandler only for the Edit wait state. Approve and Discard can be handled by a standalone `CallbackQueryHandler` added directly to the Application (not inside ConversationHandler). This avoids state machine complexity for the 2-of-3 simple cases.

---

## 2. Async SQLAlchemy Session in Bot Context

The bot process does not use FastAPI's `get_db()` dependency. Use `async_session` directly:

```python
from backend.core.database import async_session

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with async_session() as db:
        result = await process_query(db=db, ...)
        await db.commit()
```

**Transaction boundary:** `process_query` uses `db.flush()` internally (not `db.commit()`). The bot must call `await db.commit()` after `process_query` returns. Same pattern as the FastAPI endpoint.

**Audit write-back:** Open a new session for the adviser action write-back (separate transaction from the query):

```python
async def handle_approve(update, context):
    trace_id = context.user_data["trace_id"]
    async with async_session() as db:
        await audit_repo.update_adviser_action(db, trace_id, "approved", final_response=None)
        await db.commit()
```

---

## 3. TELE-02 Interpretation: Webhook Secret in Long-Polling Mode

**TELE-02:** "Telegram bot validates webhook secret on every incoming request"

**Clarification:** In long-polling mode (`run_polling()`), the bot initiates outbound HTTPS connections to `api.telegram.org/getUpdates`. There is no inbound HTTP endpoint and therefore no webhook secret to validate. The security guarantee is equivalent: only Telegram's servers can deliver updates because the bot polls Telegram directly over TLS.

**Implementation approach for TELE-02 compliance:**
- The `TELEGRAM_BOT_TOKEN` itself is the authentication credential — Telegram only delivers updates for the token's bot.
- Add a `secret_token` parameter to `Application.builder()` if using webhook mode in future. For polling mode, document that TELE-02 is satisfied by the polling architecture.
- Alternatively, interpret TELE-02 as: validate that the `TELEGRAM_BOT_TOKEN` is set and non-empty before starting the bot (fail-fast on missing config).

**Decision:** Implement TELE-02 as a startup validation — raise `ValueError` if `TELEGRAM_BOT_TOKEN` is not set. This is the meaningful security check for polling mode.

---

## 4. Identity Mapping Pattern

```python
import json
from backend.core.config import get_settings

def get_user_from_telegram_id(telegram_user_id: int) -> dict | None:
    settings = get_settings()
    user_map = json.loads(settings.telegram_user_map)  # {"123456": {"user_id": "...", "role": "adviser"}}
    return user_map.get(str(telegram_user_id))
```

Settings additions needed:
```python
telegram_bot_token: str = ""
telegram_user_map: str = "{}"  # JSON string, parsed at runtime
```

---

## 5. process_query Channel Parameter

`process_query` currently hardcodes `channel="web"` at line 39 of `query_service.py`. The fix is a one-line change: add `channel: str = "web"` parameter and pass it to `audit_service.create_audit_record`.

```python
async def process_query(
    db: AsyncSession,
    query: str,
    session_id: str | None,
    user_id: str,
    user_role: str,
    chunking_client: AsyncOpenAI,
    generation_client: AsyncOpenAI,
    qdrant_client: QdrantClient,
    channel: str = "web",  # ADD THIS
) -> dict:
    ...
    audit = await audit_service.create_audit_record(
        db, user_id, query, session_id, channel=channel  # PASS IT HERE
    )
```

---

## 6. audit_repo.update_adviser_action

New method needed:

```python
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
```

---

## 7. Test Patterns for python-telegram-bot Handlers

```python
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

def make_update(text: str, user_id: int = 12345) -> Update:
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_bot = False
    
    message = MagicMock(spec=Message)
    message.text = text
    message.from_user = user
    message.reply_text = AsyncMock()
    
    update = MagicMock(spec=Update)
    update.message = message
    update.effective_user = user
    return update

def make_context(user_data: dict = None) -> MagicMock:
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = user_data or {}
    return context
```

For callback queries:
```python
def make_callback_update(data: str, user_id: int = 12345) -> Update:
    query = MagicMock(spec=CallbackQuery)
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
    
    update = MagicMock(spec=Update)
    update.callback_query = query
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    return update
```

---

## 8. Validation Architecture

### TELE-01: Query → Answer with Citations
- Unit test: mock `process_query`, verify bot sends message containing source citations
- Integration test: send text message to handler, assert reply_text called with answer text

### TELE-02: Webhook Secret / Token Validation
- Unit test: assert bot raises ValueError on missing TELEGRAM_BOT_TOKEN
- Unit test: assert unregistered telegram_user_id returns "not registered" message

### TELE-03: Draft with Inline Keyboard
- Unit test: mock process_query, verify reply_text called with InlineKeyboardMarkup
- Unit test: verify keyboard has 3 buttons (Approve/Edit/Discard)

### TELE-04: Adviser Action in Audit Trail
- Unit test: mock audit_repo.update_adviser_action, verify called with correct trace_id and action
- Unit test: verify ConversationHandler stores trace_id in user_data
- Integration test: full flow — query → approve → assert audit record updated

---

## 9. Module Structure

```
backend/
  telegram_bot/
    __init__.py
    __main__.py          # Entry point: asyncio.run(main())
    bot.py               # Application setup, handler registration
    handlers.py          # handle_query, handle_action, handle_edit_reply
    identity.py          # get_user_from_telegram_id()
```

This keeps the bot code isolated from the FastAPI app while sharing `backend.core` and `backend.services`.

---

## 10. Dependency: python-telegram-bot

Add to `pyproject.toml`:
```toml
"python-telegram-bot[job-queue]>=22.7"
```

The `[job-queue]` extra is not strictly needed for this phase but is standard practice. Minimum: `python-telegram-bot>=22.7`.

---

## RESEARCH COMPLETE
