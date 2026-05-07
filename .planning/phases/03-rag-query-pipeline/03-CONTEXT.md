# Phase 3: RAG Query Pipeline - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Users ask natural language questions and receive accurate, source-attributed answers drawn only from approved internal documents, with every interaction audited. Scope: query enhancement → RBAC-filtered Qdrant retrieval → reranking → LLM generation → audit record. Telegram bot integration is Phase 4. Web UI is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Citation Format
- **D-01:** Numbered inline refs in the answer text (e.g., [1], [2]) with a sources list at the end.
- **D-02:** Each source entry contains: `doc_name`, `section_title`, `chunk_index`. No raw chunk text in the citation.

### Query Endpoint Shape
- **D-03:** `POST /api/v1/query` — single JSON response (no SSE streaming). Matches the existing ingest endpoint pattern.
- **D-04:** Response schema:
  ```json
  {
    "answer": "string",
    "sources": [{"doc_name": "...", "section_title": "...", "chunk_index": 0}],
    "trace_id": "string",
    "not_found": false,
    "chunks_retrieved": 5,
    "model_used": "deepseek-v4-pro"
  }
  ```

### Query Enhancement
- **D-05:** Before embedding, send the raw query to **DeepSeek V4 Flash** (`deepseek-v4-flash`) for a query rewrite — expand abbreviations, add financial domain terms. No intent classification label returned to client.
- **D-06:** The **rewritten query** is used for Voyage AI embedding. The **original user query** is sent to the reranker (cross-encoders score relevance better against natural language).
- **D-07:** Original query is preserved in the audit log alongside the rewritten version.

### Retrieval Pipeline
- **D-08:** Retrieve top 20 chunks from Qdrant (RBAC pre-filter on `allowed_roles` — same pattern as Phase 1 D-04/D-05).
- **D-09:** Rerank with `cohere/rerank-v3.5` via OpenRouter's `/api/v1/rerank` endpoint. Uses existing `OPENROUTER_API_KEY` — no new credentials. Requires a direct `httpx.AsyncClient` POST (same pattern as `embed_chunks` in `embedding_service.py`).
- **D-10:** Filter reranked chunks to those scoring >= **0.3**. If no chunks pass, proceed to LLM with empty context (triggers sentinel path).
- **D-11:** Send top 5 passing chunks to the LLM.

### Not-Found Handling
- **D-12:** Two-layer not-found detection:
  1. If no chunks pass the 0.3 reranker threshold → LLM receives empty context.
  2. System prompt instructs LLM: if provided context is empty or insufficient to answer, respond with the sentinel phrase `"NO_RELEVANT_CONTENT"` followed by a brief explanation of what the user was asking for.
- **D-13:** Query service detects the sentinel phrase in the LLM response, sets `not_found: true` in the response, and replaces the answer with a user-friendly message: "This information is not available in the approved documents."

### Generation Model
- **D-14:** Generation LLM: **`deepseek-v4-pro`** via the existing `chunking_client` (DeepSeek base URL `https://api.deepseek.com`). The `openrouter_client` is NOT used for generation.
- **D-15:** Chunking model updated to **`deepseek-v4-flash`** (replaces `deepseek-chat` which is deprecated July 2026). Same client, same base URL — only the model string changes.
- **D-16:** System prompt must: (a) instruct the LLM to answer only from the provided context chunks, (b) require inline citation markers [N] for every factual claim, (c) specify the sentinel phrase for no-relevant-content cases, (d) never reference training data or external knowledge.

### Audit Integration
- **D-17:** Audit record written **inline** (same async DB session as the request, not BackgroundTasks). Audit write failure surfaces as a query error — acceptable for compliance traceability.
- **D-18:** Audit lifecycle for queries: `received → retrieved → generated → completed` (same progressive pattern as Phase 1 D-08).
- **D-19:** Audit record stores: `original_query`, `rewritten_query`, `retrieved_doc_ids` (JSON array), `chunks_passed_rerank` (int), `sensitivity_tier_accessed`, `generated_response` (full text), `not_found` (bool), `model_used`, `prompt_tokens`, `completion_tokens`.

### Session Management
- **D-20:** Client sends optional `session_id` in the request body. Server validates: if omitted or session is expired (>24 hours since last query), a new session is created.
- **D-21:** Session expiry = 24 hours of inactivity. Expiry only sets `end_time` on the Session record — audit logs are never deleted and remain permanently queryable by compliance.
- **D-22:** Closed session audit logs are preserved forever. Next query from the same user simply opens a new session.

### Auth & Access Control
- **D-23:** All three roles can use the query endpoint: `adviser`, `senior_adviser`, `compliance`. Role is read from JWT via the existing `get_current_user` dependency and passed to Qdrant's RBAC pre-filter.

### Claude's Discretion
- Exact system prompt wording (beyond the constraints in D-16)
- Retry logic for DeepSeek/OpenRouter transient failures
- Exact error messages for Qdrant unavailability
- Query rewrite prompt design

</decisions>

<specifics>
## Specific Ideas

- Query rewrite uses DeepSeek V4 Flash (fast/cheap) — not V4 Pro. Generation uses V4 Pro (high quality).
- Reranker uses original user query (not rewritten) — cross-encoders score relevance better against natural language.
- `deepseek-chat` is deprecated July 2026 — chunking service must be updated to `deepseek-v4-flash` as part of this phase.
- OpenRouter rerank API: `POST https://openrouter.ai/api/v1/rerank` with `model: "cohere/rerank-v3.5"`, `query`, `documents[]`. Response includes `results[].relevance_score`. Same `OPENROUTER_API_KEY` as embeddings.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/REQUIREMENTS.md` §RAG-01 through RAG-05 — Full requirement text for the query pipeline
- `.planning/ROADMAP.md` §Phase 3 — Success criteria and phase boundary

### Prior phase decisions (integration points)
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — RBAC pre-filter pattern (D-04/D-05), audit progressive lifecycle (D-08), session model
- `.planning/phases/02-document-ingestion/02-CONTEXT.md` — Embedding model (Voyage AI voyage-3, 1024 dims), chunking client pattern, Qdrant metadata schema

### Existing code to read before planning
- `backend/repositories/vector_repo.py` — Qdrant search interface; extend for query retrieval
- `backend/services/embedding_service.py` — `embed_chunks` httpx pattern; rerank service follows same pattern
- `backend/services/chunking_service.py` — DeepSeek client usage; update model to `deepseek-v4-flash`; query rewrite service follows same client pattern
- `backend/repositories/audit_repo.py` — Audit record write pattern
- `backend/routers/ingest.py` — Endpoint pattern, dependency injection, response schema structure
- `backend/core/config.py` — Available API keys and settings
- `backend/models/audit_log.py` — Audit schema; may need new fields for query-specific data

### External APIs
- OpenRouter rerank API: `https://openrouter.ai/api/v1/rerank` (model: `cohere/rerank-v3.5`, $0.001/search)
- DeepSeek API docs: `https://api-docs.deepseek.com/` (models: `deepseek-v4-pro`, `deepseek-v4-flash`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `embedding_service.py` → `embed_chunks()`: direct `httpx.AsyncClient` POST to Voyage AI — rerank service follows identical pattern to OpenRouter `/rerank`
- `chunking_service.py` → DeepSeek `AsyncOpenAI` client: reuse for query rewrite (V4 Flash) and generation (V4 Pro) — only model string differs
- `vector_repo.py` → Qdrant search with RBAC pre-filter: extend with `top_k=20` parameter for query retrieval
- `audit_repo.py` → progressive lifecycle write pattern: reuse for query audit records
- `routers/ingest.py` → FastAPI endpoint pattern with `get_current_user`, `get_db`, `BackgroundTasks` dependencies
- `models/enums.py` → `SensitivityTier`, `UserRole` enums already defined

### Established Patterns
- Repository pattern: all DB/Qdrant access goes through `*_repo.py` files — query service must follow this
- Dependency injection: `get_current_user` and `get_db` via FastAPI `Depends()` — query endpoint uses both
- RBAC pre-filter: Qdrant `must` filter on `allowed_roles` payload field — query retrieval must apply this before ANN search
- Async throughout: all services use `async def` with `await` — no sync blocking calls

### Integration Points
- `vector_repo.py`: new `search_chunks(query_embedding, user_role, top_k=20)` method
- `audit_log.py` model: may need `original_query`, `rewritten_query`, `chunks_passed_rerank` fields added via Alembic migration
- `Session` model: `last_activity` field needed for 24-hour expiry check
- New router: `backend/routers/query.py` registered in `main.py`
- New services: `query_rewrite_service.py`, `rerank_service.py`, `generation_service.py`, `query_service.py` (orchestrator)

</code_context>

<deferred>
## Deferred Ideas

- SSE streaming response — Phase 5 web UI may want this; defer to that phase
- Intent classification (product lookup, client brief, compliance check) — useful for analytics but not required for RAG-01 through RAG-05
- Conversation history / multi-turn context — sessions track audit grouping only; LLM context is single-turn for now

</deferred>

---

*Phase: 03-rag-query-pipeline*
*Context gathered: 2026-05-07*
