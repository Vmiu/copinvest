---
phase: 04-telegram-bot
plan: 03
subsystem: telegram-bot
tags: [telegram, tests, audit, handlers, tdd]

requires:
  - phase: 04-telegram-bot
    plan: 01
    provides: audit_repo.update_adviser_action, process_query with channel param
  - phase: 04-telegram-bot
    plan: 02
    provides: handle_query, handle_action, handle_edit_reply, bot.main()

provides:
  - tests/test_telegram.py with 14 test functions covering TELE-01 through TELE-04

affects: []

tech-stack:
  added: []
  patterns:
    - "mock async_session context manager: __aenter__/__aexit__ AsyncMock pattern for testing handlers without live DB"
    - "seed-then-override id: create AuditLog via audit_service then override .id for deterministic trace_id in tests"

key-files:
  created:
    - tests/test_telegram.py
  modified:
    - backend/telegram_bot/handlers.py

key-decisions:
  - "handler bug fix: handle_action passed raw callback data ('approve', 'discard') to update_adviser_action instead of enum-compatible values ('approved', 'discarded') — fixed inline per Rule 1"
  - "seed pattern: use audit_service.create_audit_record then override .id for deterministic trace_ids — matches test_audit.py style"

metrics:
  duration: ~25min
  completed: 2026-05-09
  tasks: 2
  files_created: 1
  files_modified: 1
---

# Phase 04 Plan 03: Telegram Bot Tests Summary

**14 tests covering audit write-back, channel tagging, and the full Approve/Edit/Discard handler flow — plus a Rule 1 bug fix in handle_action**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-05-09
- **Tasks:** 2/2
- **Files created:** 1
- **Files modified:** 1

## Accomplishments

- `tests/test_telegram.py` with 14 test functions:
  - 5 tests for `audit_repo.update_adviser_action`: approve, edited, discard, unknown trace_id (ValueError), flush-not-commit
  - 4 tests for `handle_query`: unregistered user, draft with InlineKeyboardMarkup (3 buttons), trace_id stored in user_data, pipeline error returns generic message
  - 3 tests for `handle_action`: approve calls update_adviser_action with "approved" + llm_response, edit returns AWAITING_EDIT, discard calls update_adviser_action with "discarded"
  - 1 test for `handle_edit_reply`: calls update_adviser_action with "edited" + replacement text
  - 1 test for `bot.main()`: raises ValueError when telegram_bot_token is empty
- Bug fix in `backend/telegram_bot/handlers.py`: `handle_action` now maps callback data to enum-compatible strings before calling `update_adviser_action`

## Task Commits

1. **Rule 1 fix: map callback data to AdviserAction enum values** — `96e7ed1` (fix)
2. **Task 1+2: 14 tests for Telegram bot audit write-back and handlers** — `366e92c` (test)

## Files Created/Modified

- `tests/test_telegram.py` — 14 test functions, 289 lines; covers TELE-01 through TELE-04
- `backend/telegram_bot/handlers.py` — fixed `handle_action` to pass `"approved"`/`"discarded"` instead of `"approve"`/`"discard"` to `update_adviser_action`

## Decisions Made

- Seed pattern: `audit_service.create_audit_record` then override `.id` — matches existing `test_audit.py` style exactly
- Mock `async_session` as a context manager with `__aenter__`/`__aexit__` AsyncMocks — cleanest way to test handlers without a live DB
- Handler tests import from `backend.telegram_bot.handlers` directly and patch at module level

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AdviserAction enum mismatch in handle_action**
- **Found during:** Task 1 test execution (test_handle_action_approve and test_handle_action_discard failed)
- **Issue:** `handle_action` passed raw callback data (`"approve"`, `"discard"`) to `audit_repo.update_adviser_action`, which calls `AdviserAction(action)`. The enum values are `"approved"` and `"discarded"` — `AdviserAction("approve")` raises `ValueError` in production.
- **Fix:** Added `audit_action` variable mapping `"approve"` → `"approved"` and `"discard"` → `"discarded"` before the `update_adviser_action` call.
- **Files modified:** `backend/telegram_bot/handlers.py`
- **Commit:** `96e7ed1`

## Known Stubs

None.

## Threat Flags

No new network endpoints or auth paths introduced. Test file only.

## Threat Model Coverage

- T-04-09 (Tampering — unknown trace_id): `test_update_adviser_action_unknown_trace_id` verifies ValueError is raised — no silent no-op.
- T-04-10 (Information Disclosure — pipeline error): `test_handle_query_pipeline_error` verifies generic "Something went wrong" message is sent — internal exception details not leaked.

## Self-Check: PASSED

- `tests/test_telegram.py` confirmed on disk
- `backend/telegram_bot/handlers.py` confirmed modified
- Commits `96e7ed1` and `366e92c` confirmed in git log
- `uv run pytest tests/test_telegram.py -v` — 14 passed
- `uv run pytest tests/ -q` — 74 passed, 2 skipped, no regressions
