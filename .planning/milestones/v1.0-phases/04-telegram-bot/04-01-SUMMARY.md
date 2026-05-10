---
phase: 04-telegram-bot
plan: 01
subsystem: api
tags: [telegram, audit, query-service, settings, python-telegram-bot]

requires:
  - phase: 03-query-pipeline
    provides: process_query, audit_service.create_audit_record, AuditLog model with channel/adviser fields

provides:
  - process_query with channel parameter (defaults to "web", accepts "telegram")
  - audit_repo.update_adviser_action for writing Approve/Edit/Discard back to AuditLog
  - Settings.telegram_bot_token and Settings.telegram_user_map fields
  - python-telegram-bot>=22.7 declared in pyproject.toml

affects: [04-02-bot-core, 04-03-conversation-handler]

tech-stack:
  added: [python-telegram-bot>=22.7]
  patterns:
    - "channel parameter forwarding: process_query passes channel=channel to create_audit_record"
    - "flush-not-commit: update_adviser_action uses db.flush() so caller controls transaction boundary"

key-files:
  created: []
  modified:
    - backend/services/query_service.py
    - backend/repositories/audit_repo.py
    - backend/core/config.py
    - pyproject.toml

key-decisions:
  - "update_adviser_action uses db.flush() not db.commit() — bot ConversationHandler controls the transaction"
  - "telegram_user_map stored as JSON string in Settings (not a dict) to stay compatible with pydantic-settings env var parsing"
  - "channel defaults to 'web' in process_query signature for full backwards compatibility with existing web API callers"

patterns-established:
  - "channel parameter: all query pipeline entry points should pass channel= to create_audit_record"
  - "adviser action write-back: update_adviser_action is the single write path for all three action types"

requirements-completed: [TELE-01, TELE-02, TELE-04]

duration: 85min
completed: 2026-05-09
---

# Phase 04 Plan 01: Telegram Bot Backend Wiring Summary

**Surgical backend changes: channel parameter on process_query, update_adviser_action in audit_repo, Telegram settings in config, and python-telegram-bot dependency**

## Performance

- **Duration:** ~85 min (across two sessions)
- **Started:** 2026-05-09T03:08:40+08:00
- **Completed:** 2026-05-09T04:33:34+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- process_query now accepts `channel: str = "web"` and forwards it to create_audit_record, enabling Telegram audit records tagged as "telegram"
- audit_repo.update_adviser_action added — single write path for Approve/Edit/Discard actions, uses db.flush() so the bot's ConversationHandler controls the transaction
- Settings exposes telegram_bot_token and telegram_user_map with safe empty defaults, readable from .env
- python-telegram-bot>=22.7 declared in pyproject.toml

## Task Commits

1. **Task 1 RED: Failing tests for channel param and update_adviser_action** - `c1dc573` (test)
2. **Task 1 GREEN: Add channel param to process_query and update_adviser_action to audit_repo** - `8d5c9ae` (feat)
3. **Task 2: Add Telegram settings to Settings and python-telegram-bot to pyproject.toml** - `41ef0a4` (feat)

## Files Created/Modified
- `backend/services/query_service.py` - Added `channel: str = "web"` parameter, changed hardcoded `channel="web"` to `channel=channel`
- `backend/repositories/audit_repo.py` - Added `update_adviser_action` function with AdviserAction enum mapping and db.flush()
- `backend/core/config.py` - Added `telegram_bot_token: str = ""` and `telegram_user_map: str = "{}"` fields
- `pyproject.toml` - Added `python-telegram-bot>=22.7` to dependencies

## Decisions Made
- `update_adviser_action` uses `db.flush()` not `db.commit()` — the bot's ConversationHandler will own the transaction boundary, not the repo function
- `telegram_user_map` is a JSON string field (not `dict`) because pydantic-settings parses env vars as strings; the bot will `json.loads()` it at startup
- `channel` defaults to `"web"` in `process_query` for full backwards compatibility — no changes needed to existing web API callers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — no UI-facing stubs introduced. telegram_bot_token and telegram_user_map have empty defaults that will be validated at bot startup in plan 04-02.

## Threat Flags

No new network endpoints, auth paths, or schema changes introduced. telegram_bot_token is a settings field with empty default — never logged or returned in API responses.

## Next Phase Readiness
- Backend wiring complete. Plan 04-02 (bot core) can now call `process_query(..., channel="telegram")` and `update_adviser_action(...)` directly.
- Bot startup should validate `settings.telegram_bot_token != ""` before starting the Application.
- `telegram_user_map` JSON parsing and validation belongs in plan 04-02 bot initialization.

---
*Phase: 04-telegram-bot*
*Completed: 2026-05-09*
