---
phase: 02-document-ingestion
plan: "04"
subsystem: api
tags: [fastapi, qdrant, sqlalchemy, pytest, rbac, ingest]

requires:
  - phase: 02-document-ingestion/02-01
    provides: DocumentRecord, document_repo, vector_repo, IngestResponse, require_role
  - phase: 02-document-ingestion/02-02
    provides: chunking_service.chunk_document, embedding_service.embed_chunks
  - phase: 02-document-ingestion/02-03
    provides: ingestion_service.ingest_document

provides:
  - POST /api/v1/ingest — file upload endpoint with compliance RBAC and sensitivity tier assignment
  - Integration test suite (11 tests) covering all 8 INGEST requirements
  - document_repo.upsert_document_record bug fix (ingested_at NOT NULL on re-ingestion)

affects: []

tech-stack:
  added: []
  patterns:
    - "UploadFile + Form fields — multipart/form-data endpoint pattern for file + metadata"
    - "patch() context managers for mocking _parse_document (sync), chunk_document (async), embed_chunks (async)"
    - "qdrant_memory fixture with setup_collection() — in-process Qdrant for integration tests"

key-files:
  created:
    - backend/routers/ingest.py
    - tests/test_ingestion.py
  modified:
    - backend/main.py
    - backend/repositories/document_repo.py

key-decisions:
  - "require_role('compliance') dependency on endpoint — 403 for any non-compliance role (T-02-01)"
  - "user_id from current_user['user_id'] not 'sub' — matches get_current_user return shape (dependencies.py)"
  - "setup_collection(client) in qdrant_memory fixture — in-memory Qdrant needs collection before upsert"
  - "ingested_at not overwritten on upsert update path — preserves original ingestion timestamp"

patterns-established:
  - "Multipart ingest endpoint: UploadFile = File(...), SensitivityTier = Form(...), optional document_id = Form(None)"
  - "Integration test with patched heavy deps: _parse_document (sync mock), chunk_document/embed_chunks (AsyncMock)"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08]

duration: 6min
completed: "2026-05-06"
---

# Phase 2 Plan 04: API Endpoint and Integration Tests Summary

**POST /api/v1/ingest with require_role("compliance") RBAC, SensitivityTier form validation, and 11 integration tests covering all 8 INGEST requirements via mocked OpenAI and in-memory Qdrant**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-06
- **Completed:** 2026-05-06
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `POST /api/v1/ingest` endpoint accepts multipart file + sensitivity_tier + optional document_id; enforces compliance-only access via `require_role("compliance")`
- SensitivityTier enum validation on Form field rejects invalid values at FastAPI layer (T-02-04)
- All parse/chunk failures raise HTTP 422 via ValueError/RuntimeError catch (D-17)
- 11 integration tests cover INGEST-01 through INGEST-08: file types (PDF/DOCX/CSV), RBAC 403, tier-to-roles Qdrant payload, chunk metadata, re-ingestion replacement, UUID document_id, quality metrics, unsupported file, empty file
- Tests mock all heavy dependencies (docling, OpenAI) — run in ~4 seconds

## Task Commits

1. **Task 1: Create ingest router** — `9373d2c` (feat)
2. **Task 2: Register ingest router in main.py** — `53d704e` (feat)
3. **Task 3: Integration tests** — `4a54480` (feat)

**Plan metadata:** *(this commit)*

## Files Created/Modified
- `backend/routers/ingest.py` — POST /api/v1/ingest: require_role, File+Form params, ValueError/RuntimeError→422
- `backend/main.py` — Added ingest router import and app.include_router(ingest_router)
- `tests/test_ingestion.py` — 11 integration tests with in-memory Qdrant and patched OpenAI services
- `backend/repositories/document_repo.py` — Bug fix: removed ingested_at assignment in upsert update path

## Decisions Made
- `current_user["user_id"]` not `current_user["sub"]` — `get_current_user()` in `dependencies.py` returns `{"user_id": ..., "role": ...}` not JWT claims directly
- `setup_collection(client)` in test fixture — in-memory Qdrant starts empty; collection must exist before upsert or `delete_by_source` is called
- `ingested_at` excluded from upsert update fields — the SQLAlchemy default lambda only fires on INSERT, not on a Python-level copy; overwriting with `None` broke the NOT NULL constraint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `upsert_document_record` overwriting `ingested_at=None` on re-ingestion**
- **Found during:** Task 3 (test_reingest_replaces_chunks)
- **Issue:** `upsert_document_record` copied `record.ingested_at` to the existing record during update. A freshly constructed `DocumentRecord(...)` has `ingested_at=None` before flush — the SQLAlchemy `default=lambda` only fires on INSERT. Setting `existing.ingested_at = None` then violated the NOT NULL constraint.
- **Fix:** Removed the `existing.ingested_at = record.ingested_at` line in the update path (original ingestion timestamp preserved)
- **Files modified:** `backend/repositories/document_repo.py`
- **Commit:** `4a54480`

**2. [Rule 1 - Bug] Fixed `current_user["sub"]` KeyError in plan spec**
- **Found during:** Task 1 (reviewing dependencies.py)
- **Issue:** Plan spec used `current_user["sub"]` but `get_current_user()` returns `{"user_id": ..., "role": ...}` — accessing `"sub"` would raise KeyError at runtime
- **Fix:** Used `current_user["user_id"]` in the endpoint implementation
- **Files modified:** `backend/routers/ingest.py`
- **Commit:** `9373d2c`

**3. [Rule 1 - Bug] Added `setup_collection()` call to `qdrant_memory` test fixture**
- **Found during:** Task 3 (all ingestion tests failing with "Collection documents not found")
- **Issue:** In-memory Qdrant client starts with no collections; `vector_repo.upsert_chunks` and `delete_by_source` require the collection to exist
- **Fix:** Called `setup_collection(client)` in the `qdrant_memory` fixture before returning
- **Files modified:** `tests/test_ingestion.py`
- **Commit:** `4a54480`

## Known Stubs

None — all 11 test cases exercise real code paths with mocked external dependencies.

## Threat Flags

No new network endpoints, auth paths, or trust boundaries introduced beyond the POST /api/v1/ingest endpoint already documented in the plan's threat model (T-02-01 through T-02-04).

---
*Phase: 02-document-ingestion*
*Completed: 2026-05-06*

## Self-Check: PASSED

- FOUND: backend/routers/ingest.py
- FOUND: backend/main.py (contains `from backend.routers.ingest import router as ingest_router`)
- FOUND: tests/test_ingestion.py
- FOUND: backend/repositories/document_repo.py
- FOUND: 9373d2c (Task 1 commit)
- FOUND: 53d704e (Task 2 commit)
- FOUND: 4a54480 (Task 3 commit)
- VERIFIED: 42 passed, 2 skipped across full test suite
