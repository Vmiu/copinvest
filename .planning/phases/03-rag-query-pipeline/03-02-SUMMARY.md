---
plan: "03-02"
phase: "03-rag-query-pipeline"
status: complete
completed: 2026-05-07
---

# Summary: Core RAG Services

## What Was Built

Four query pipeline services implementing the full RAG intelligence layer, plus generation client singleton wiring.

## Key Files Created/Modified

### Created
- `backend/services/query_rewrite_service.py` — DeepSeek V4 Flash query rewriter with graceful fallback to original query on API error
- `backend/services/rerank_service.py` — OpenRouter cohere/rerank-v3.5 reranker; filters to threshold ≥ 0.3, top_n=5; falls back to top-N by Qdrant score on httpx error
- `backend/services/generation_service.py` — DeepSeek V4 Pro answer generator with inline [N] citation extraction, NO_RELEVANT_CONTENT sentinel detection, and compliance-aware system prompt
- `backend/services/query_service.py` — Full pipeline orchestrator: session → audit → rewrite → embed (Voyage AI) → retrieve (Qdrant RBAC) → rerank → generate → update audit

### Modified
- `backend/services/session_service.py` — Extended `get_or_create_session` to accept optional `session_id: str | None` parameter; if supplied, looks up that session directly and validates 24h timeout
- `backend/core/dependencies.py` — Added `_generation_client` singleton, `get_generation_client()` getter, updated `init_clients()` to accept 4th `generation_client` parameter
- `backend/main.py` — Added `generation_client` (DeepSeek V4 Pro, same API key as chunking_client), passed to `init_clients()`

## Self-Check: PASSED

- ✓ `rewrite_query` uses `deepseek-v4-flash`, falls back on `APIConnectionError/RateLimitError/APIError`
- ✓ `rerank_chunks` filters `relevance_score >= 0.3`, falls back on `httpx.HTTPError`
- ✓ `generate_answer` system prompt contains `NO_RELEVANT_CONTENT` sentinel; uses `deepseek-v4-pro`; extracts `[N]` citations via `re.findall`
- ✓ `process_query` wraps Qdrant in `asyncio.to_thread`; uses original query for reranker (D-06); calls `update_query_fields`
- ✓ `get_generation_client()` importable; `init_clients()` accepts 4 params
- ✓ `main.py` creates `generation_client` with `deepseek_api_key`
- ✓ All existing tests pass (42 passed, 2 skipped)

## Notes

Agent timed out mid-execution (Cloudflare 524). Recovered uncommitted `generation_service.py`, `query_service.py`, and `session_service.py` from worktree before cleanup. Task 3 (dependencies.py + main.py) completed inline by orchestrator.
