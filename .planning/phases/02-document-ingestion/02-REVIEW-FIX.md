---
phase: 02-document-ingestion
fixed_at: 2026-05-06T00:00:00Z
review_path: .planning/phases/02-document-ingestion/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-06
**Source review:** .planning/phases/02-document-ingestion/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (3 Critical, 5 Warning)
- Fixed: 8
- Skipped: 0

## Fixed Issues

### CR-01: JWT `role` claim not validated — wrong HTTP status and inconsistent auth state

**Files modified:** `backend/core/dependencies.py`
**Commit:** 9ce68b4
**Applied fix:** Changed `if user_id is None:` to `if user_id is None or role is None:` so a JWT missing the `role` claim raises 401 Unauthorized rather than passing through and causing a misleading 403 Forbidden downstream.

---

### CR-02: No atomicity between Qdrant delete and insert — data loss window on re-ingestion

**Files modified:** `backend/repositories/vector_repo.py`, `backend/services/ingestion_service.py`
**Commit:** 2e0e2d4
**Applied fix:** Reversed the order to write-then-replace. `upsert_chunks` now returns `(count, point_ids)`. A new `delete_by_source_except_new(client, source_id, new_point_ids)` function scrolls for existing points and deletes only those not in the new set. `ingestion_service.ingest_document` now calls upsert first, then delete — eliminating the gap where a failed upsert leaves the document with zero chunks.

---

### CR-03: No file size limit — unbounded memory allocation on upload

**Files modified:** `backend/routers/ingest.py`
**Commit:** 6f0af06
**Applied fix:** Added `MAX_UPLOAD_BYTES = 50 * 1024 * 1024` constant and changed `await file.read()` to `await file.read(MAX_UPLOAD_BYTES + 1)` followed by a size check that raises HTTP 413 if the limit is exceeded.

---

### WR-01: Retry loop in `chunk_document` retries non-transient errors
### WR-02: Chunk splitter is fragile when LLM output starts with `---`

**Files modified:** `backend/services/chunking_service.py`
**Commit:** a2cc791
**Applied fix (WR-01):** Replaced `except Exception` with specific `except (APIConnectionError, RateLimitError, APIError)` for transient errors. Added `except ValueError: raise` before it so `ValueError("LLM returned no chunks")` propagates immediately without retrying. Added imports for `APIConnectionError`, `APIError`, `RateLimitError` from `openai`.
**Applied fix (WR-02):** Replaced `raw.split("\n---\n")` with `raw.strip()`, normalize CRLF, then `re.split(r'\n?^---$\n?', normalized, flags=re.MULTILINE)` to handle LLM outputs that start with `---` without a leading newline.

---

### WR-03: `embed_chunks` has no guard against empty input

**Files modified:** `backend/services/embedding_service.py`
**Commit:** a77d491
**Applied fix:** Added `if not chunks: raise ValueError("embed_chunks called with empty chunk list")` before the OpenAI API call, so an empty chunk list produces a descriptive 422 instead of an opaque OpenAI API error.

---

### WR-04: OpenAI and Qdrant clients created per ingestion request
### WR-05: Qdrant startup failure swallows exception details

**Files modified:** `backend/core/dependencies.py`, `backend/main.py`, `backend/routers/ingest.py`, `backend/services/ingestion_service.py`, `tests/test_ingestion.py`
**Commit:** 6dc5d57
**Applied fix (WR-04):** Added `_openai_client` and `_qdrant_client` module-level singletons to `dependencies.py`, with `init_clients()`, `get_openai_client()`, and `get_qdrant_client()` functions. `main.py` lifespan now creates one `AsyncOpenAI` and one `QdrantClient` instance and calls `init_clients`. The router uses `Depends(get_openai_client)` and `Depends(get_qdrant_client)`, and passes them into `ingestion_service.ingest_document` (which now accepts them as parameters instead of constructing them inline). Integration tests updated to override `get_qdrant_client` and `get_openai_client` via `app.dependency_overrides` instead of using `patch()`.
**Applied fix (WR-05):** Changed `except Exception:` in `main.py` lifespan to `except Exception as exc:` and added `error=str(exc)` and `error_type=type(exc).__name__` fields to the `logger.warning()` call.

---

_Fixed: 2026-05-06_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
