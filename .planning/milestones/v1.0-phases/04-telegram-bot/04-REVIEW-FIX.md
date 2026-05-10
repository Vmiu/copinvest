---
phase: "04"
fixed_at: "2026-05-09T00:00:00Z"
review_path: .planning/phases/04-telegram-bot/04-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-05-09
**Source review:** .planning/phases/04-telegram-bot/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: handle_action registered outside ConversationHandler

**Files modified:** `backend/telegram_bot/bot.py`
**Commit:** 2b745ac
**Applied fix:** Removed the standalone `app.add_handler(CallbackQueryHandler(handle_action))` call. Added `CallbackQueryHandler(handle_action)` to both `entry_points` and the `AWAITING_EDIT` state list inside the `ConversationHandler`. Also added `per_message=False` explicitly to match the intended per-user/per-chat conversation tracking.

### CR-02: session_id missing from process_query return dict

**Files modified:** `backend/services/query_service.py`
**Commit:** cb338a2
**Applied fix:** Added `"session_id": session_id` to the return dict in `process_query`, alongside the existing `trace_id`, `answer`, `sources`, and other fields.

### CR-03: json.loads in identity.py not guarded against JSONDecodeError

**Files modified:** `backend/telegram_bot/identity.py`
**Commit:** 590b4d0
**Applied fix:** Wrapped `json.loads(settings.telegram_user_map)` in a `try/except json.JSONDecodeError` block that logs the error via structlog and returns `None`. Combined with WR-01 in the same commit since both touch the same function.

### WR-01: Role not validated against UserRole enum in identity.py

**Files modified:** `backend/telegram_bot/identity.py`
**Commit:** 590b4d0
**Applied fix:** After retrieving the entry from the user map, extracted the `role` field and checked it against `{r.value for r in UserRole}`. If the role is not a valid enum value, logs a warning and returns `None`. Added `structlog` and `UserRole` imports.

### WR-02: update.effective_user not guarded against None in handlers.py

**Files modified:** `backend/telegram_bot/handlers.py`
**Commit:** f0aaeaa
**Applied fix:** Added a `None` guard at the top of `handle_query`: if `update.effective_user is None`, return `ConversationHandler.END` immediately before accessing `.id`.

### WR-03: httpx in [dev] dependencies instead of main dependencies

**Files modified:** `pyproject.toml`
**Commit:** 9491acf
**Applied fix:** Moved `"httpx>=0.28.0"` from `[project.optional-dependencies] dev` to the main `[project] dependencies` list. httpx is a runtime dependency of python-telegram-bot and must be present in production installs.

### WR-04: Two DB sessions opened in handle_action approve path

**Files modified:** `backend/telegram_bot/handlers.py`
**Commit:** d357014
**Applied fix:** Consolidated the approve path from two sequential `async with async_session()` blocks (one to fetch `llm_response`, one to call `update_adviser_action`) into a single session that does both operations. The discard path already used one session; restructured the if/else so each branch opens exactly one session when `trace_id` is present.

## Test Results

```
uv run pytest tests/ -q
74 passed, 2 skipped, 1 warning in 8.00s
```

All 74 tests pass. The 2 skipped and 1 warning are pre-existing and unrelated to these fixes.

---

_Fixed: 2026-05-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
