---
phase: 03-rag-query-pipeline
verified: 2026-05-07T15:00:00Z
status: passed
score: 18/18 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 3: RAG Query Pipeline Verification Report

**Phase Goal:** Users can ask natural language questions and receive accurate, source-attributed answers drawn only from approved documents, with every interaction audited
**Verified:** 2026-05-07T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User receives an answer from POST /api/v1/query with answer, sources, trace_id, not_found, chunks_retrieved, model_used | VERIFIED | router returns QueryResponse(**result); test_query_endpoint_happy_path PASSED |
| 2 | Unauthenticated request returns 401 | VERIFIED | require_role dependency calls get_current_user which raises 401 on missing token; test_query_unauthenticated PASSED |
| 3 | Request from disallowed role returns 403 | VERIFIED | require_role enforces allowlist ["adviser", "senior_adviser", "compliance"]; raises HTTP 403 on mismatch |
| 4 | When no chunks pass reranker threshold, response has not_found=true and answer contains "not available" | VERIFIED | generation_service detects NO_RELEVANT_CONTENT sentinel; sets answer = "This information is not available in the approved documents."; test_query_not_found PASSED |
| 5 | Audit record is created in DB for every successful query | VERIFIED | audit_service.create_audit_record called at step 2 of process_query before pipeline runs; test_query_audit_record PASSED |
| 6 | RBAC filter is applied at Qdrant layer using role from JWT | VERIFIED | user_role from JWT passed to query_with_rbac; test_query_rbac_enforcement confirms role comes from JWT not request body |
| 7 | 11 tests pass in tests/test_query.py (6 integration + 5 unit) | VERIFIED | uv run pytest tests/test_query.py: 11 passed, 0 skipped, 0 failed |
| 8 | User receives graceful degradation when query rewrite service is unavailable | VERIFIED | rewrite_query catches APIConnectionError/RateLimitError/APIError and returns original query |
| 9 | rerank_service filters chunks to threshold >= 0.3 via cohere/rerank-v3.5 | VERIFIED | rerank_service.py lines 47-49; test_rerank_threshold PASSED (2 of 4 chunks pass 0.3 threshold) |
| 10 | generation_service generates answer with inline [N] citations and detects NO_RELEVANT_CONTENT sentinel | VERIFIED | _extract_sources uses re.findall(r'\[(\d+)\]'); sentinel detection on line 77; test_citation_extraction and test_not_found_sentinel PASSED |
| 11 | query_service orchestrates full pipeline: session -> audit -> rewrite -> embed -> retrieve -> rerank -> generate -> update audit | VERIFIED | query_service.py steps 1-10 all present and wired; update_query_fields called at step 9 |
| 12 | generation_client singleton exists in dependencies.py and is initialised in main.py lifespan | VERIFIED | _generation_client global + get_generation_client() in dependencies.py; generation_client created in lifespan with deepseek_api_key |
| 13 | AuditLog model has rewritten_query, chunks_passed_rerank, not_found columns | VERIFIED | audit_log.py lines 44-46; all three Mapped columns present |
| 14 | Session model has last_activity column | VERIFIED | audit_log.py line 17; last_activity Mapped column on Session |
| 15 | audit_service has update_query_fields() function | VERIFIED | audit_service.py lines 60-69 |
| 16 | session_service uses 24h timeout and updates last_activity on each call | VERIFIED | SESSION_TIMEOUT = timedelta(hours=24); last_activity = now set on session reuse; test_session_24h_timeout PASSED |
| 17 | Alembic migration adds rewritten_query, chunks_passed_rerank, not_found to audit_log and last_activity to sessions | VERIFIED | a1b2c3d4e5f6_add_query_pipeline_fields.py; upgrade() adds all 4 columns; downgrade() reverses them |
| 18 | Full test suite passes without regressions | VERIFIED | uv run pytest tests/ -q: 53 passed, 2 skipped (pre-existing), 0 failed |

**Score:** 18/18 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/a1b2c3d4e5f6_add_query_pipeline_fields.py` | DB migration for query pipeline columns | VERIFIED | Adds 4 columns; chained from 23b31f0ac9b4; upgrade/downgrade present |
| `backend/models/audit_log.py` | Updated AuditLog and Session models | VERIFIED | rewritten_query, chunks_passed_rerank, not_found on AuditLog; last_activity on Session |
| `backend/services/audit_service.py` | update_query_fields function | VERIFIED | Function at lines 60-69; sets 3 fields and calls db.flush() |
| `backend/services/session_service.py` | 24h session timeout with last_activity tracking | VERIFIED | SESSION_TIMEOUT = timedelta(hours=24); last_activity updated on reuse; optional session_id param |
| `backend/services/query_rewrite_service.py` | async rewrite_query(query, client) -> str | VERIFIED | Uses deepseek-v4-flash; falls back on APIConnectionError/RateLimitError/APIError |
| `backend/services/rerank_service.py` | async rerank_chunks(query, chunks, api_key, threshold, top_n) -> list | VERIFIED | cohere/rerank-v3.5; threshold filter; httpx fallback |
| `backend/services/generation_service.py` | async generate_answer(query, chunks, client) -> dict | VERIFIED | deepseek-v4-pro; NO_RELEVANT_CONTENT sentinel; [N] citation extraction via re.findall |
| `backend/services/query_service.py` | async process_query(...) -> dict | VERIFIED | All 10 pipeline steps present; asyncio.to_thread for Qdrant; original query for reranker |
| `backend/schemas/query.py` | QueryRequest, QueryResponse, SourceCitation Pydantic models | VERIFIED | All 3 classes present and importable |
| `backend/routers/query.py` | POST /api/v1/query endpoint | VERIFIED | router registered; require_role enforces 3 roles; calls process_query |
| `backend/core/dependencies.py` | get_generation_client() singleton | VERIFIED | _generation_client global; getter; init_clients accepts 4 params |
| `backend/main.py` | query_router included; generation_client in lifespan | VERIFIED | query_router imported and included; generation_client created with deepseek_api_key |
| `tests/test_query.py` | 11 passing integration + unit tests | VERIFIED | 11 tests, 0 skipped, 0 failed; min_lines satisfied (410 lines) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/routers/query.py` | `backend/services/query_service.py` | `await query_service.process_query(...)` | WIRED | Line 34 of query.py |
| `backend/routers/query.py` | `backend/core/dependencies.py` | `Depends(require_role), Depends(get_generation_client)` | WIRED | Lines 26, 29 of query.py |
| `backend/services/query_service.py` | `backend/repositories/vector_repo.py` | `asyncio.to_thread(query_with_rbac, ...)` | WIRED | Line 65 of query_service.py |
| `backend/services/query_service.py` | `backend/services/audit_service.py` | `update_query_fields, update_generation` | WIRED | Lines 91-97 of query_service.py |
| `backend/services/generation_service.py` | `query_service.py` | `NO_RELEVANT_CONTENT sentinel detection` | WIRED | gen["not_found"] consumed at query_service line 92 |
| `backend/main.py` | `backend/routers/query.py` | `app.include_router(query_router)` | WIRED | Line 58 of main.py |
| `tests/test_query.py` | `POST /api/v1/query` | `async_client.post('/api/v1/query', json=...)` | WIRED | Multiple test functions |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `backend/routers/query.py` | `result` dict | `query_service.process_query()` | Yes — orchestrates live pipeline | FLOWING |
| `backend/services/query_service.py` | `chunks` | `asyncio.to_thread(query_with_rbac, ...)` | Yes — Qdrant RBAC query | FLOWING |
| `backend/services/query_service.py` | `reranked` | `rerank_service.rerank_chunks(...)` | Yes — OpenRouter API with threshold filter | FLOWING |
| `backend/services/query_service.py` | `gen` | `generation_service.generate_answer(...)` | Yes — DeepSeek V4 Pro completion | FLOWING |
| `backend/services/generation_service.py` | `sources` | `_extract_sources(answer, chunks)` | Yes — re.findall on LLM response | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 11 query tests pass | `uv run pytest tests/test_query.py -v` | 11 passed, 0 failed | PASS |
| Full suite no regressions | `uv run pytest tests/ -q` | 53 passed, 2 skipped, 0 failed | PASS |
| /api/v1/query route registered | Python import check on app.routes | Route present | PASS |
| query_rewrite_service importable | Import check | OK | PASS |
| generation_client singleton importable | Import check | OK | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RAG-01 | 03-01, 03-02, 03-03 | User can ask a natural language question and receive an answer sourced from internal documents | SATISFIED | POST /api/v1/query returns answer; test_query_endpoint_happy_path PASSED |
| RAG-02 | 03-02, 03-03 | Every response includes inline source citations with document name and section reference | SATISFIED | sources list with doc_name, section_title, chunk_index in QueryResponse; _extract_sources wired |
| RAG-03 | 03-02, 03-03 | System returns "not found in approved documents" when retrieval confidence is below threshold | SATISFIED | NO_RELEVANT_CONTENT sentinel + "not available in the approved documents" answer; test_query_not_found PASSED |
| RAG-04 | 03-02, 03-03 | Retrieved chunks are reranked by a cross-encoder before being sent to the LLM | SATISFIED | rerank_service uses cohere/rerank-v3.5 via OpenRouter; threshold=0.3; test_rerank_threshold PASSED |
| RAG-05 | 03-02, 03-03 | System prompt constrains the LLM to answer only from provided context, never from training data | SATISFIED | GENERATION_PROMPT contains "ONLY the provided context chunks" and "Never use your training data or external knowledge"; NO_RELEVANT_CONTENT sentinel enforced |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/rerank_service.py` | 24 | `return []` | Info | Early-exit guard for empty input — not a stub; correct behavior when no chunks provided |

No blockers or warnings found. The single `return []` is a legitimate guard clause, not a stub — it fires only when `chunks` is empty on entry, before any data-fetching occurs.

### Human Verification Required

None. All must-haves are verifiable programmatically and all tests pass.

### Gaps Summary

No gaps. All 18 must-haves verified. All 5 requirement IDs (RAG-01 through RAG-05) satisfied. Full test suite passes with no regressions.

---

_Verified: 2026-05-07T15:00:00Z_
_Verifier: Kiro (gsd-verifier)_
