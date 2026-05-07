---
phase: 03-rag-query-pipeline
plan: "03-03"
subsystem: query-api
tags: [fastapi, pydantic, query-endpoint, integration-tests, rbac]
dependency_graph:
  requires:
    - 03-02 (query_service.process_query, generation_service, rerank_service, query_rewrite_service)
    - 01-02 (JWT auth, require_role, get_current_user)
    - 01-01 (AuditLog model, get_settings)
  provides:
    - POST /api/v1/query endpoint
    - QueryRequest, QueryResponse, SourceCitation Pydantic schemas
    - 11 passing tests covering RAG-01 through RAG-05
  affects:
    - backend/main.py (query_router registered)
tech_stack:
  added: []
  patterns:
    - FastAPI router with require_role dependency (same pattern as ingest router)
    - process_query patched at service boundary for endpoint-level integration tests
    - httpx.AsyncClient patched as context manager for Voyage AI embed mock
key_files:
  created:
    - backend/schemas/query.py
    - backend/routers/query.py
  modified:
    - backend/main.py
    - tests/test_query.py
decisions:
  - "Role injected from JWT via require_role(adviser, senior_adviser, compliance) — not from request body (T-3-01)"
  - "ValueError → 422, RuntimeError → 500 — internal error details not leaked (T-3-04)"
  - "db.commit() called after successful process_query return — audit record persisted atomically with response"
  - "Integration tests patch process_query at service boundary; audit tests patch at lowest external boundaries (httpx, vector_repo, sub-services)"
  - "httpx.AsyncClient patched as class-level context manager (not .post directly) to match async with pattern in query_service"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-07T14:41:53Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 3 Plan 03: Query Endpoint and Integration Tests Summary

POST /api/v1/query endpoint wiring process_query pipeline into FastAPI with Pydantic schemas, RBAC enforcement, and 11 passing tests covering happy path, not-found, unauthenticated, RBAC, audit record, session timeout, and all five service unit tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Schemas and query router | 408b38a | backend/schemas/query.py, backend/routers/query.py, backend/main.py |
| 2 | Integration tests | 56b07ae | tests/test_query.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected httpx mock pattern for async context manager**
- **Found during:** Task 2
- **Issue:** Plan's mock used `patch("httpx.AsyncClient.post")` with `__aenter__`/`__aexit__` on the return value, but `query_service.py` uses `async with httpx.AsyncClient(...) as http: resp = await http.post(...)` — the context manager is on the `AsyncClient` instance, not on `.post()`. Patching `.post` as a context manager would not intercept the actual call.
- **Fix:** Patched `httpx.AsyncClient` as the class, set `__aenter__` to return a mock instance with `.post` returning the mock Voyage AI response.
- **Files modified:** tests/test_query.py
- **Commit:** 56b07ae

## Known Stubs

None — all response fields are wired from process_query return dict.

## Threat Flags

No new security surface introduced beyond what is in the plan's threat model. The query endpoint enforces T-3-01 (role from JWT), T-3-04 (error detail sanitization), and T-3-03 (audit record inline).

## Self-Check: PASSED

- [x] backend/schemas/query.py exists
- [x] backend/routers/query.py exists
- [x] backend/main.py includes query_router
- [x] tests/test_query.py: 11 tests, 0 skipped, 0 failed
- [x] Full suite: 53 passed, 2 skipped (pre-existing), 0 failed
- [x] Commits 408b38a and 56b07ae exist in git log
