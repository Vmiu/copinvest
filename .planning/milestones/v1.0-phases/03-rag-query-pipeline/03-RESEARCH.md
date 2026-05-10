# Phase 3: RAG Query Pipeline — Research

**Researched:** 2026-05-07
**Status:** Complete

---

## 1. Component Breakdown

### 1.1 Query Rewrite (DeepSeek V4 Flash)

**Reuse:** `chunking_service.py` DeepSeek `AsyncOpenAI` client pattern — same client, same base URL, different model string.

```python
# Pattern from chunking_service.py — reuse exactly
response = await client.chat.completions.create(
    model="deepseek-v4-flash",   # was deepseek-chat
    messages=[
        {"role": "system", "content": REWRITE_PROMPT},
        {"role": "user", "content": original_query},
    ],
    temperature=0.0,
)
rewritten = response.choices[0].message.content.strip()
```

**Error handling:** Wrap in try/except for `APIConnectionError`, `RateLimitError`, `APIError` — on failure, fall back to original query (rewrite is enhancement, not blocker).

**Prompt constraints:** Expand abbreviations, add financial domain terms, return only the rewritten query string (no explanation).

---

### 1.2 Embedding (Voyage AI voyage-3)

**Reuse:** `embedding_service.embed_chunks()` — identical httpx pattern, but use `input_type: "query"` instead of `"document"`.

```python
async with httpx.AsyncClient(timeout=60) as http:
    resp = await http.post(
        VOYAGE_EMBED_URL,
        headers={"Authorization": f"Bearer {settings.voyage_api_key}", ...},
        json={"model": "voyage-3", "input": [rewritten_query], "input_type": "query"},
    )
resp.raise_for_status()
query_vector = resp.json()["data"][0]["embedding"]  # single vector
```

**Key difference from ingestion:** `input_type: "query"` (not `"document"`) — Voyage AI optimizes differently for query vs document embeddings.

---

### 1.3 Retrieval (Qdrant RBAC pre-filter)

**Reuse:** `vector_repo.query_with_rbac()` — already implements RBAC pre-filter on `allowed_roles`. Pass `limit=20`.

**Critical:** `vector_repo.py` uses the **sync** `QdrantClient`. Must wrap in `asyncio.to_thread()`:

```python
import asyncio
results = await asyncio.to_thread(
    query_with_rbac, qdrant_client, query_vector, user_role, limit=20
)
chunks = results.points  # list of ScoredPoint
```

Each `ScoredPoint.payload` contains: `text`, `source_id`, `doc_type`, `sensitivity_tier`, `allowed_roles`, `chunk_index`, `section_title`.

---

### 1.4 Reranking (OpenRouter cohere/rerank-v3.5)

**Reuse:** `embedding_service.py` httpx pattern — direct `httpx.AsyncClient` POST.

```python
async with httpx.AsyncClient(timeout=30) as http:
    resp = await http.post(
        "https://openrouter.ai/api/v1/rerank",
        headers={
            "Authorization": f"Bearer {settings.openroute_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "cohere/rerank-v3.5",
            "query": original_query,   # D-06: original query, not rewritten
            "documents": [pt.payload["text"] for pt in chunks],
            "top_n": len(chunks),
        },
    )
resp.raise_for_status()
results = resp.json()["results"]  # [{index, relevance_score}, ...]
```

**Threshold filter:** Keep only results where `relevance_score >= 0.3`. Take top 5 of passing results.

**Not-found trigger:** If zero results pass threshold → proceed to generation with empty context (triggers sentinel path per D-12).

**Error handling:** On reranker failure, fall back to top 5 by Qdrant score (log warning, do not fail request).

---

### 1.5 Generation (DeepSeek V4 Pro)

**Reuse:** Same `chunking_client` (DeepSeek base URL), model `deepseek-v4-pro`.

**System prompt must:**
1. Instruct LLM to answer only from provided context chunks
2. Require inline citation markers `[N]` for every factual claim
3. Specify sentinel phrase `NO_RELEVANT_CONTENT` when context is empty/insufficient
4. Prohibit referencing training data or external knowledge

**Context format:** Number each chunk `[1]`, `[2]`, etc. Include `doc_name` and `section_title` as chunk header.

**Sentinel detection:** After LLM response, check `"NO_RELEVANT_CONTENT" in response_text`. If found: set `not_found=True`, replace answer with user-friendly message.

**Citation parsing:** Extract `[N]` markers from answer text, map to source list using chunk index.

---

## 2. New Files to Create

| File | Responsibility |
|------|---------------|
| `backend/services/query_rewrite_service.py` | Rewrite query via DeepSeek V4 Flash |
| `backend/services/rerank_service.py` | Rerank chunks via OpenRouter cohere/rerank-v3.5 |
| `backend/services/generation_service.py` | Generate answer via DeepSeek V4 Pro with citation extraction |
| `backend/services/query_service.py` | Orchestrate full pipeline: rewrite → embed → retrieve → rerank → generate → audit |
| `backend/routers/query.py` | POST /api/v1/query endpoint |
| `backend/schemas/query.py` | QueryRequest and QueryResponse Pydantic models |

---

## 3. Files to Modify

| File | Change |
|------|--------|
| `backend/services/chunking_service.py` | Update `model="deepseek-chat"` → `model="deepseek-v4-flash"` (line ~55 in `_chunk_page`) |
| `backend/models/audit_log.py` | Add new columns: `original_query`, `rewritten_query`, `chunks_passed_rerank`, `not_found` to `AuditLog`; add `last_activity` to `Session` |
| `backend/services/audit_service.py` | Add `update_query_fields()` function for new columns; update `create_audit_record()` to accept `original_query` |
| `backend/services/session_service.py` | Change `SESSION_TIMEOUT` from 30min to 24h; add `last_activity` update on each query |
| `backend/core/config.py` | No changes needed — `openroute_api_key` and `voyage_api_key` already present |
| `backend/main.py` | Import and register `query_router` |

---

## 4. Alembic Migration

### New columns on `audit_log` table

```sql
ALTER TABLE audit_log ADD COLUMN original_query TEXT;
ALTER TABLE audit_log ADD COLUMN rewritten_query TEXT;
ALTER TABLE audit_log ADD COLUMN chunks_passed_rerank INTEGER;
ALTER TABLE audit_log ADD COLUMN not_found BOOLEAN DEFAULT FALSE;
```

### New column on `sessions` table

```sql
ALTER TABLE sessions ADD COLUMN last_activity TIMESTAMP WITH TIME ZONE;
```

**Migration name:** `add_query_pipeline_fields`

**Note:** `query_text` already exists on `AuditLog` — `original_query` is a new field that stores the same value for query records (for clarity in audit trail). Alternatively, `original_query` can be stored in `query_text` and `rewritten_query` added as new. Recommend keeping `query_text` as-is and adding `rewritten_query` only (simpler migration, `query_text` = original query).

**Revised migration (simpler):**
```sql
ALTER TABLE audit_log ADD COLUMN rewritten_query TEXT;
ALTER TABLE audit_log ADD COLUMN chunks_passed_rerank INTEGER;
ALTER TABLE audit_log ADD COLUMN not_found BOOLEAN DEFAULT FALSE;
ALTER TABLE sessions ADD COLUMN last_activity TIMESTAMP WITH TIME ZONE;
```

---

## 5. API Contract

### Request: POST /api/v1/query

```json
{
  "query": "string (required)",
  "session_id": "string (optional)"
}
```

**Auth:** Bearer JWT (all three roles: adviser, senior_adviser, compliance)

### Response: 200 OK

```json
{
  "answer": "string",
  "sources": [
    {
      "doc_name": "string",
      "section_title": "string",
      "chunk_index": 0
    }
  ],
  "trace_id": "string",
  "not_found": false,
  "chunks_retrieved": 5,
  "model_used": "deepseek-v4-pro"
}
```

**Error responses:**
- `401` — invalid/expired JWT
- `403` — role not in [adviser, senior_adviser, compliance]
- `422` — invalid request body
- `500` — pipeline failure (Qdrant unavailable, DeepSeek error after retries)

---

## 6. Validation Architecture

### Test Scenarios (RAG-01 through RAG-05)

**RAG-01: Natural language Q&A**
- POST /api/v1/query with a question that has matching content in Qdrant
- Assert: response.answer is non-empty, response.not_found is false
- Assert: HTTP 200

**RAG-02: Inline source citations**
- POST /api/v1/query with a question that retrieves chunks
- Assert: response.sources is non-empty list
- Assert: each source has doc_name, section_title, chunk_index
- Assert: answer text contains at least one [N] citation marker

**RAG-03: Not-found handling**
- POST /api/v1/query with a question that has no matching content (e.g., "What is the weather today?")
- Assert: response.not_found is true
- Assert: response.answer contains "not available in the approved documents"
- Assert: response.sources is empty list

**RAG-04: Reranking applied**
- POST /api/v1/query — verify audit record has chunks_passed_rerank <= 5
- Assert: audit log chunks_passed_rerank field is populated
- Unit test: rerank_service returns results sorted by relevance_score descending

**RAG-05: System prompt constraint**
- POST /api/v1/query with a question about general knowledge not in documents
- Assert: response.not_found is true (LLM does not answer from training data)
- Unit test: generation_service system prompt contains "only from the provided context"

**RBAC enforcement (cross-cutting)**
- POST /api/v1/query as adviser role — assert no Restricted/Confidential chunks in sources
- POST /api/v1/query as compliance role — assert Confidential chunks accessible

**Audit completeness**
- POST /api/v1/query — assert audit record created with trace_id, user_id, query_text, rewritten_query, retrieved_chunks, model_used, not_found

---

## 7. Plan Decomposition

### Plan 1: Schema Migration + Model Updates
- Alembic migration: add `rewritten_query`, `chunks_passed_rerank`, `not_found` to `audit_log`; add `last_activity` to `sessions`
- Update `AuditLog` and `Session` SQLAlchemy models
- Update `audit_service.py`: add `update_query_fields()`, update `create_audit_record()`
- Update `session_service.py`: 24h timeout, `last_activity` tracking
- Update `chunking_service.py`: model string `deepseek-chat` → `deepseek-v4-flash`
- Tests: migration applies cleanly, session timeout is 24h

### Plan 2: Query Pipeline Services
- `query_rewrite_service.py` — DeepSeek V4 Flash rewrite with fallback
- `rerank_service.py` — OpenRouter cohere/rerank-v3.5 with threshold filter
- `generation_service.py` — DeepSeek V4 Pro with citation extraction and sentinel detection
- `query_service.py` — orchestrator: rewrite → embed → retrieve → rerank → generate → audit
- Unit tests for each service

### Plan 3: Query Endpoint + Integration Tests
- `backend/schemas/query.py` — QueryRequest, QueryResponse, SourceCitation Pydantic models
- `backend/routers/query.py` — POST /api/v1/query with auth, session handling
- Register router in `main.py`
- Integration tests: happy path, not-found, RBAC enforcement, audit record creation

---

## Key Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Sync Qdrant client blocks event loop | Wrap `query_with_rbac()` in `asyncio.to_thread()` |
| `openroute_api_key` typo in config.py | Use exact field name — do not "fix" the typo (breaking change) |
| DeepSeek V4 Flash rewrite adds latency | Rewrite is fast (flash model); acceptable for non-streaming endpoint |
| Reranker returns no results above 0.3 | Proceed with empty context → sentinel path → not_found response |
| Session 24h expiry vs current 30min | Migration: add `last_activity` column; session_service change is backward-compatible |
| `deepseek-chat` deprecation July 2026 | Update in Plan 1 — chunking_service.py model string change |

---

## RESEARCH COMPLETE
