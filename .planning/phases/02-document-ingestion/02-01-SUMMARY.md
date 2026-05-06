---
phase: 02-document-ingestion
plan: "01"
subsystem: database
tags: [sqlalchemy, alembic, qdrant, pydantic, fastapi, sqlite]

requires:
  - phase: 01-data-foundation
    provides: Base model, User model, AuditLog, vector_repo RBAC, get_settings, get_current_user

provides:
  - DocumentRecord SQLAlchemy model (document_registry table)
  - Alembic migration for document_registry
  - document_repo async CRUD functions
  - vector_repo upsert_chunks and delete_by_source
  - IngestResponse Pydantic schema
  - require_role dependency helper
  - openai_api_key in Settings

affects: [02-02-ingest-endpoint, 02-03-parser, 02-04-chunking]

tech-stack:
  added: []
  patterns:
    - "Repository pattern: async SQLAlchemy functions with db.flush() — caller controls transaction boundary"
    - "Qdrant upsert: UUID point IDs with payload_base spread pattern for chunk metadata"
    - "RBAC dependency: require_role(*roles) factory wrapping get_current_user with HTTP 403"

key-files:
  created:
    - backend/models/document.py
    - backend/repositories/document_repo.py
    - backend/schemas/ingest.py
    - alembic/versions/23b31f0ac9b4_add_document_registry.py
    - tests/test_chunking.py
  modified:
    - backend/core/config.py
    - backend/core/dependencies.py
    - backend/models/__init__.py
    - backend/repositories/vector_repo.py
    - alembic/env.py

key-decisions:
  - "openai_api_key has no default — forces explicit env config, never logged (T-02-05)"
  - "upsert_document_record uses db.flush() not commit — caller controls transaction boundary (established pattern)"
  - "upsert_chunks generates UUID point IDs — avoids ID conflicts across re-ingestion cycles"

patterns-established:
  - "Payload index for source_id (KEYWORD) added to setup_collection() — enables delete_by_source filter"
  - "require_role(*roles) factory pattern for role-based endpoint protection"

requirements-completed: [INGEST-04, INGEST-05, INGEST-08]

duration: 15min
completed: "2026-05-06"
---

# Phase 2 Plan 01: Foundation — Models, Migration, Repos, Config, Schemas Summary

**SQLAlchemy DocumentRecord model, Alembic migration, document/vector repos, IngestResponse schema, and require_role RBAC dependency — all data-layer foundations for ingestion pipeline**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-06T19:25:00Z
- **Completed:** 2026-05-06T19:40:00Z
- **Tasks:** 8
- **Files modified:** 9

## Accomplishments
- DocumentRecord model maps to `document_registry` table with all INGEST-08 quality metric fields (chunk_count, total_chars, parse_duration_ms, extraction_method, warnings)
- Alembic migration auto-generated and verified with `alembic upgrade head`; ForeignKey to `users.id` and unique index on `document_id`
- vector_repo extended with `upsert_chunks` (UUID IDs, payload spread) and `delete_by_source` (filter by source_id payload field) for ingestion and re-ingestion
- `require_role` dependency factory enables compliance-only endpoint restriction (D-11)
- Wave 0 test stubs for INGEST-06/07 placed for Plan 02-04 to implement

## Task Commits

1. **Task 1: Add openai_api_key to Settings** - `943f03a` (feat)
2. **Task 2: Create DocumentRecord model** - `c314f00` (feat)
3. **Task 3: Alembic migration for document_registry** - `d14807c` (feat)
4. **Task 4: Create document_repo** - `8be15a5` (feat)
5. **Task 5: Extend vector_repo** - `9a5cc50` (feat)
6. **Task 6: Create ingest schemas** - `14be0d0` (feat)
7. **Task 7: Add require_role dependency** - `6254f2a` (feat)
8. **Task 8: Wave 0 test stubs** - `c11a795` (test)

## Files Created/Modified
- `backend/core/config.py` - Added openai_api_key field (no default, env-forced)
- `backend/models/document.py` - DocumentRecord with all INGEST-08 fields, FK to users.id
- `backend/models/__init__.py` - Export DocumentRecord
- `alembic/versions/23b31f0ac9b4_add_document_registry.py` - Migration: document_registry table
- `alembic/env.py` - Import backend.models.document for autogenerate detection
- `backend/repositories/document_repo.py` - get_document_by_id, upsert_document_record
- `backend/repositories/vector_repo.py` - Added PointStruct, uuid, source_id index, upsert_chunks, delete_by_source
- `backend/schemas/ingest.py` - IngestResponse Pydantic model
- `backend/core/dependencies.py` - require_role(*allowed_roles) factory
- `tests/test_chunking.py` - Wave 0 stub tests (skipped, for Plan 02-04)

## Decisions Made
- `openai_api_key` has no default value — matches `secret_key` pattern, forces explicit environment config (T-02-05 compliance)
- `upsert_chunks` generates UUID point IDs via `str(uuid.uuid4())` — avoids collision when re-ingesting same document
- `delete_by_source` uses Qdrant `Filter(must=[FieldCondition(...)])` — consistent with existing `query_with_rbac` pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added OPENAI_API_KEY placeholder to .env**
- **Found during:** Task 1 (add openai_api_key to Settings)
- **Issue:** After adding `openai_api_key: str` with no default, all tests failed because existing `.env` did not have the key, causing `ValidationError` on `get_settings()` import
- **Fix:** Appended `OPENAI_API_KEY=placeholder-set-real-key-for-production` to `.env` (gitignored)
- **Files modified:** `.env` (gitignored, not committed)
- **Verification:** `uv run pytest tests/ -q` passed (31 passed) after adding placeholder
- **Committed in:** Not committed (`.env` is gitignored)

**2. [Rule 2 - Missing Critical] Imported backend.models.document in alembic/env.py**
- **Found during:** Task 3 (Alembic migration)
- **Issue:** alembic autogenerate did not detect DocumentRecord because env.py only imported `backend.models.user` — new model invisible to schema comparison
- **Fix:** Added `import backend.models.document` to `alembic/env.py` (same pattern as existing user import)
- **Files modified:** `alembic/env.py`
- **Verification:** autogenerate detected `document_registry` table and generated correct migration
- **Committed in:** `d14807c` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both auto-fixes necessary for correct operation. No scope creep.

## Issues Encountered
- None beyond the deviations documented above.

## User Setup Required
Set real `OPENAI_API_KEY` in `.env` before running ingestion (placeholder currently set for dev):
```
OPENAI_API_KEY=sk-...your-key...
```

## Next Phase Readiness
- All data-layer foundations in place for Plan 02-02 (ingest endpoint)
- `require_role("compliance")` ready to protect the upload endpoint
- `upsert_chunks` and `delete_by_source` ready for Plan 02-03/02-04 pipeline integration
- `upsert_document_record` ready for Plan 02-02 to persist document registry entries

---
*Phase: 02-document-ingestion*
*Completed: 2026-05-06*
