---
phase: "03"
fixed_at: "2026-05-08T00:03:30+08:00"
review_path: .planning/phases/03-rag-query-pipeline/03-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-05-08T00:03:30+08:00
**Source review:** .planning/phases/03-rag-query-pipeline/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 10
- Fixed: 10
- Skipped: 0

## Fixed Issues

### CR-01 + WR-04: Audit record lost on pipeline failure / error path skips commit

**Files modified:** `backend/models/enums.py`, `backend/services/audit_service.py`, `backend/services/query_service.py`
**Commit:** b898466
**Applied fix:** Added `error` to `AuditStatus` enum. Added `update_error()` to `audit_service`. In `query_service.process_query`, the initial audit record is now committed immediately after creation (`await db.commit()`) before the pipeline starts. The entire pipeline is wrapped in `try/except Exception`; on failure, `update_error()` is called and committed before re-raising. This ensures the audit record survives any downstream exception.

### CR-02: Prompt injection — no max_length on query field

**Files modified:** `backend/schemas/query.py`, `backend/services/generation_service.py`
**Commit:** 391f2bc
**Applied fix:** Added `max_length=2000` to `QueryRequest.query` via `Field(..., min_length=1, max_length=2000)`. In `generation_service.py`, the user query is now wrapped in `<user_question>...</user_question>` XML tags to structurally separate it from trusted context in the LLM prompt.

### CR-03: Session hijacking — no ownership check on caller-supplied session_id

**Files modified:** `backend/services/session_service.py`
**Commit:** a0e6f9a
**Applied fix:** After fetching a session by `session_id`, added `if session and session.user_id != user_id: session = None` before checking expiry. A mismatched session is treated as not found, causing a new session to be created rather than allowing cross-user session access.

### CR-04: API keys threaded through call chain as plain string args

**Files modified:** `backend/services/rerank_service.py`, `backend/routers/query.py`
**Commit:** 22030df
**Applied fix:** Removed `api_key: str` parameter from `rerank_chunks()` — it now calls `get_settings().openroute_api_key` internally. Removed `voyage_api_key` and `openroute_api_key` parameters from `process_query()` — voyage key is read from `get_settings()` inside the embed block. Removed `settings = get_settings()` and the two key arguments from the router call site. Removed the now-unused `get_settings` import from the router.

### WR-01: Timezone-naive comparison in session timeout

**Files modified:** `backend/services/session_service.py`
**Commit:** a0e6f9a
**Applied fix:** Removed `cutoff_naive` and all `.replace(tzinfo=None)` stripping. Both the `session_id` and no-`session_id` paths now compare `activity_time` directly against `cutoff` (both timezone-aware). If a stored datetime lacks tzinfo (legacy data), it is coerced to UTC via `activity_time.replace(tzinfo=timezone.utc)` rather than stripping the cutoff.

### WR-02: Rerank fallback returns unfiltered results

**Files modified:** `backend/services/rerank_service.py`
**Commit:** 22030df
**Applied fix:** Changed the `except httpx.HTTPError` fallback from `return chunks[:top_n]` to `return []`. Returning unfiltered Qdrant results bypasses the 0.3 threshold and could produce low-confidence answers. Returning empty causes the generation step to emit `NO_RELEVANT_CONTENT`, which is the correct safe behavior.

### WR-03: `prompt_sent` audit column always stored as `""`

**Files modified:** `backend/services/generation_service.py`, `backend/services/query_service.py`
**Commit:** 391f2bc (generation_service), b898466 (query_service)
**Applied fix:** `generate_answer()` now returns `"prompt_sent": user_message` in its result dict. In `query_service`, `update_retrieval()` is called after generation with `gen["prompt_sent"]` instead of the hardcoded `""`.

### WR-04: `db.commit()` only on success path

See CR-01 above — fixed in the same commit (b898466). The `except` block now calls `await db.commit()` after `update_error()`.

### WR-05: `test_session.py` async tests missing `@pytest.mark.asyncio`

**Files modified:** `tests/test_session.py`
**Commit:** 5fb22e7
**Applied fix:** Added `import pytest` and `@pytest.mark.asyncio` decorator to all three async test functions: `test_create_session`, `test_reuse_active_session`, `test_expire_inactive_session`. All 3 tests pass (`3 passed in 0.04s`).

### WR-06: `session_id` accepts arbitrary strings with no UUID format validation

**Files modified:** `backend/schemas/query.py`
**Commit:** 391f2bc
**Applied fix:** Added `pattern=r'^[0-9a-f-]{36}$'` to the `session_id` field via `Field(None, pattern=...)`. This rejects non-UUID strings at the Pydantic validation layer before they reach the database query.

---

_Fixed: 2026-05-08T00:03:30+08:00_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
