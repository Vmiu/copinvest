---
phase: 01-data-foundation
plan: 04
subsystem: vector-store
tags: [qdrant, rbac, pre-filtering, vector-search]

requires:
  - phase: 01-01
    provides: FastAPI app skeleton, config with qdrant_host/port/collection
  - phase: 01-02
    provides: JWT auth with role in payload, get_current_user dependency
provides:
  - Qdrant collection setup with 1536-dim cosine vectors and payload indexes
  - RBAC-filtered vector query (pre-retrieval must filter on allowed_roles)
  - get_qdrant_client factory for Qdrant connection
affects: [02-ingestion, 03-rag-pipeline]

tech-stack:
  added: []
  patterns: [Qdrant pre-filtering with must FieldCondition on allowed_roles, in-memory QdrantClient for tests]

key-files:
  created:
    - backend/repositories/vector_repo.py
    - tests/test_vector_repo.py
  modified:
    - backend/main.py
    - .gitignore

key-decisions:
  - "Used get_settings() inside functions (not module-level) for testability -- consistent with Plan 01/02 pattern"
  - "RBAC filtering uses single MatchValue on allowed_roles -- Qdrant pre-filters before ANN search"
  - "Lifespan wraps Qdrant init in try/except so app starts without Docker running"

patterns-established:
  - "Vector repo: sync functions (qdrant-client is sync), called from async context"
  - "RBAC: pre-retrieval filtering via Qdrant must filter on allowed_roles payload field"
  - "Testing: in-memory QdrantClient(':memory:') for zero-dependency vector store tests"

requirements-completed: [AUTH-04, AUTH-05]

duration: 3min
completed: 2026-04-29
---

# Phase 01 Plan 04: Qdrant Vector Repository with RBAC Summary

**Qdrant vector repository with pre-retrieval RBAC filtering using must conditions on allowed_roles payload, proving AUTH-04 (pre-filtering) and AUTH-05 (adviser blocked from tier 3-4)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-29T13:26:23Z
- **Completed:** 2026-04-29T13:29:37Z
- **Tasks:** 2 (TDD: 2 commits -- 1 RED + 1 GREEN)
- **Files modified:** 4

## Accomplishments
- Qdrant collection setup with 1536-dimension cosine vectors and payload indexes on allowed_roles (KEYWORD) and sensitivity_tier (INTEGER)
- RBAC-filtered query using Qdrant pre-retrieval must filter on allowed_roles -- no post-retrieval filtering
- Lifespan initializes Qdrant collection at startup with graceful fallback if Qdrant unavailable
- 5 passing tests proving D-05 role-tier mapping: adviser=tier1 only, senior_adviser=tiers1-3, compliance=all tiers
- AUTH-05 proven: adviser gets zero results when only restricted/confidential points exist

## Task Commits

Each task followed TDD (RED then GREEN):

1. **RED: Failing tests for Qdrant RBAC filtering** - `a093504` (test)
2. **GREEN: Implement vector_repo, update lifespan, extend .gitignore** - `935e7a1` (feat)

## Files Created/Modified
- `backend/repositories/vector_repo.py` - Qdrant collection setup + RBAC-filtered query (get_qdrant_client, setup_collection, query_with_rbac)
- `tests/test_vector_repo.py` - 5 tests with in-memory Qdrant: setup, adviser filter, senior filter, compliance filter, adviser blocked
- `backend/main.py` - Added Qdrant collection initialization in lifespan with try/except fallback
- `.gitignore` - Extended with .pytest_cache, egg-info, dist, build, .venv

## Decisions Made
- Used `get_settings()` inside functions (not at module level) for testability -- consistent with the pattern established in Plans 01 and 02
- RBAC filtering uses a single `MatchValue` on `allowed_roles` -- Qdrant applies this as a pre-filter before approximate nearest neighbor search, which is the security-correct model (no post-retrieval filtering)
- Lifespan wraps Qdrant init in try/except so the app starts even without Docker running -- tests use in-memory Qdrant and don't need the Docker container

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `a093504` (test) -- 5 failing tests committed before implementation
- GREEN gate: `935e7a1` (feat) -- implementation making all tests pass
- REFACTOR gate: Not needed -- code was clean after GREEN

## Issues Encountered
None

## User Setup Required
None - tests use in-memory Qdrant. Docker container only needed for running the app.

## Next Phase Readiness
- Vector repository ready for Phase 2 document ingestion (setup_collection creates the collection, ingestion pipeline upserts points with allowed_roles and sensitivity_tier payloads)
- query_with_rbac ready for Phase 3 RAG pipeline (accepts query vector + user role, returns filtered results)
- Phase 1 Data Foundation complete -- all 4 plans executed

## Self-Check: PASSED

- All 4 key files verified present on disk
- All 2 task commits verified in git log (a093504, 935e7a1)

---
*Phase: 01-data-foundation*
*Completed: 2026-04-29*
