---
phase: 02-document-ingestion
plan: "03"
subsystem: api
tags: [docling, openai, qdrant, sqlalchemy, fastapi, rag, ingestion]

requires:
  - phase: 02-document-ingestion/02-01
    provides: DocumentRecord model, document_repo.upsert_document_record, vector_repo.upsert_chunks, vector_repo.delete_by_source
  - phase: 02-document-ingestion/02-02
    provides: chunking_service.chunk_document, embedding_service.embed_chunks

provides:
  - ingestion_service.ingest_document() — full pipeline: docling parse → LLM chunk → embed → Qdrant store → DB record
  - docling>=2.12.0 added to pyproject.toml
  - TIER_TO_ROLES mapping from SensitivityTier to allowed_roles list

affects: [02-04-ingest-endpoint]

tech-stack:
  added:
    - "docling>=2.12.0"
  patterns:
    - "CPU-bound sync work wrapped in asyncio.to_thread() — docling DocumentConverter is synchronous"
    - "OpenAI client constructed at call site from get_settings() — consistent with chunking/embedding injection pattern"
    - "tempfile.NamedTemporaryFile(suffix=suffix) — original filename never used as filesystem path (T-02-02)"

key-files:
  created:
    - backend/services/ingestion_service.py
  modified:
    - pyproject.toml

key-decisions:
  - "TIER_TO_ROLES maps SensitivityTier enum members to allowed_roles list — Qdrant payload enforces RBAC pre-filtering at DB layer"
  - "delete_by_source before upsert — idempotent re-ingestion replaces existing chunks (D-12)"
  - "document_id optional — UUID generated if omitted, enables human-readable slugs when provided (D-14)"

patterns-established:
  - "Ingestion pipeline: parse (docling) → chunk (gpt-4o-mini) → embed (text-embedding-3-small) → store (Qdrant) → record (SQLite)"

requirements-completed: [INGEST-01, INGEST-02, INGEST-03, INGEST-08]

duration: 2min
completed: "2026-05-06"
---

# Phase 2 Plan 03: Ingestion Orchestration Service Summary

**docling parse → gpt-4o-mini chunk → text-embedding-3-small embed → Qdrant upsert → DocumentRecord persist, with idempotent re-ingestion via delete_by_source and RBAC tier-to-roles mapping**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-06T11:40:16Z
- **Completed:** 2026-05-06T11:42:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `ingest_document()` orchestrates the complete ingestion pipeline as a single async function callable by the router
- CPU-bound docling parsing runs in a thread pool via `asyncio.to_thread()` — never blocks the event loop
- `TIER_TO_ROLES` maps all 4 sensitivity tiers to `allowed_roles` lists, injecting RBAC into Qdrant payload at ingestion time
- Re-ingestion is idempotent: `delete_by_source` removes existing chunks before upserting new ones (D-12)
- Quality metrics (chunk_count, total_chars, parse_duration_ms, extraction_method) persisted to DocumentRecord (D-16)
- Path traversal mitigated: `tempfile.NamedTemporaryFile(suffix=ext)` uses a generated temp path; original filename only stored in DB (T-02-02)

## Task Commits

1. **Task 1: Add docling to pyproject.toml** - `e9e6549` (chore)
2. **Task 2: Create ingestion_service.py** - `a973c76` (feat)

**Plan metadata:** *(this commit)*

## Files Created/Modified
- `backend/services/ingestion_service.py` — Full pipeline: parse → chunk → embed → store → record; TIER_TO_ROLES; DOC_TYPE_MAP; path-safe tempfile handling
- `pyproject.toml` — Added docling>=2.12.0 to core dependencies

## Decisions Made
- `TIER_TO_ROLES` uses SensitivityTier enum members as keys — since `SensitivityTier` is `int, enum.Enum`, keys hash identically to their integer values, making lookup by `.value` work correctly
- OpenAI client constructed inside `ingest_document()` from `get_settings()` — consistent with the chunking/embedding pattern (services receive injected clients)

## Deviations from Plan

None — plan executed exactly as written. `openai>=1.68.0` was already present in `pyproject.toml` from plan 02-02; only `docling>=2.12.0` needed to be added.

## Issues Encountered
None.

## User Setup Required
None — real `OPENAI_API_KEY` was already required from Plan 02-01. No new external services.

## Next Phase Readiness
- `ingest_document(db, file_content, filename, sensitivity_tier, user_id, document_id)` ready for Plan 02-04 (ingest router) to call
- Returns a dict matching `IngestResponse` schema fields
- Raises `ValueError` on empty parse or unsupported file type — Plan 02-04 router should catch and return HTTP 422
- Raises `RuntimeError` on LLM chunking failure — Plan 02-04 router should catch and return HTTP 422

---
*Phase: 02-document-ingestion*
*Completed: 2026-05-06*

## Self-Check: PASSED

- FOUND: backend/services/ingestion_service.py
- FOUND: .planning/phases/02-document-ingestion/02-03-SUMMARY.md
- FOUND: e9e6549 (Task 1 commit)
- FOUND: a973c76 (Task 2 commit)
