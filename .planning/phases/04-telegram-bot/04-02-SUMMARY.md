---
phase: 04-telegram-bot
plan: 02
subsystem: telegram-bot
tags: [telegram, bot, handlers, identity, conversation-handler, python-telegram-bot]

requires:
  - phase: 04-telegram-bot
    plan: 01
    provides: process_query with channel param, update_adviser_action, telegram settings in config

provides:
  - backend/telegram_bot package (5 files)
  - get_user_from_telegram_id: static identity lookup from telegram_user_map JSON
  - handle_query: RAG pipeline invocation with channel="telegram", inline keyboard response
  - handle_action: approve/edit/discard callback handler with audit write-back
  - handle_edit_reply: adviser replacement text recorder
  - main(): bot entry point with token validation and client setup
  - uv run python -m backend.telegram_bot entry point

affects: [04-03-conversation-handler]

tech-stack:
  added: []
  patterns:
    - "bot_data pattern: AsyncOpenAI and QdrantClient created once in main(), stored in app.bot_data, read in handlers via context.bot_data"
    - "user_data trace_id: trace_id stored in context.user_data after process_query, read in handle_action and handle_edit_reply for audit write-back"
    - "standalone CallbackQueryHandler: handle_action registered outside ConversationHandler so it fires regardless of conversation state"

key-files:
  created:
    - backend/telegram_bot/__init__.py
    - backend/telegram_bot/identity.py
    - backend/telegram_bot/bot.py
    - backend/telegram_bot/handlers.py
    - backend/telegram_bot/__main__.py
  modified: []

key-decisions:
  - "bot_data used for shared clients (not dependency injection) — matches python-telegram-bot idiomatic pattern"
  - "handle_action registered as standalone CallbackQueryHandler outside ConversationHandler — ensures approve/discard work even if conversation state is END"
  - "base_url set to https://api.deepseek.com/v1 matching backend/main.py lifespan exactly"
  - "conversation_timeout=300 (5 min) per plan D-06 discretion"

metrics:
  duration: ~20min
  completed: 2026-05-09
  tasks: 2
  files_created: 5
  files_modified: 0
---

# Phase 04 Plan 02: Telegram Bot Core Summary

**5-file telegram_bot package: identity lookup, RAG query handler, approve/edit/discard action handler, ConversationHandler wiring, and standalone entry point**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-05-09
- **Tasks:** 2/2
- **Files created:** 5

## Accomplishments

- `backend/telegram_bot/__init__.py`: package marker
- `identity.py`: `get_user_from_telegram_id` parses `telegram_user_map` JSON from settings, returns `{"user_id", "role"}` or None for unregistered users
- `bot.py`: `main()` validates `TELEGRAM_BOT_TOKEN`, creates `AsyncOpenAI` (deepseek) and `QdrantClient` instances, stores them in `app.bot_data`, registers `CallbackQueryHandler` and `ConversationHandler`
- `handlers.py`: `handle_query` runs RAG pipeline with `channel="telegram"`, stores `trace_id` in `user_data`, sends draft with Approve/Edit/Discard inline keyboard; `handle_action` handles all three actions with audit write-back; `handle_edit_reply` records adviser replacement text
- `__main__.py`: `asyncio.run(main())` entry point — bot starts with `uv run python -m backend.telegram_bot`

## Task Commits

1. **Task 1: Package skeleton with identity.py and bot.py** — `ba5581e`
2. **Task 2: handlers.py and __main__.py** — `f668e34`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new network endpoints introduced. Bot reads from Telegram's API (inbound only). All trust boundary mitigations from the plan's threat model are implemented:
- T-04-04: unregistered users rejected before any query processing
- T-04-05: `update_adviser_action` uses `AdviserAction(action)` enum validation
- T-04-06: exceptions logged server-side only; generic message returned to user
- T-04-08: role read from static admin-configured map, not from user input

## Self-Check: PASSED

All 5 created files confirmed on disk. Both task commits (ba5581e, f668e34) confirmed in git log.
