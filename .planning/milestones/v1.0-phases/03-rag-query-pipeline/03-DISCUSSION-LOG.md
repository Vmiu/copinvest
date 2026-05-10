# Phase 3: RAG Query Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 03-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-07
**Phase:** 03-rag-query-pipeline
**Mode:** discuss (interactive)
**Areas discussed:** Citation format, Query endpoint shape, Reranker choice, Not-found threshold, Generation model, Pipeline depth, Audit integration, Auth & role access, Session management, Query enhancement

---

## Discussion Log

### Citation Format

| Question | Options | Selection |
|----------|---------|-----------|
| What should source citations look like? | Numbered inline refs + sources list / Inline parenthetical / Structured JSON | Numbered inline refs + sources list |
| What fields in each source entry? | doc_name + section_title + chunk_index / + excerpt / doc_name + page only | doc_name + section_title + chunk_index |

### Query Endpoint Shape

| Question | Options | Selection |
|----------|---------|-----------|
| Streaming or single response? | Single JSON / SSE streaming | Single JSON response |
| Response schema? | {answer, sources, trace_id, not_found} / + chunks_retrieved, model_used | {answer, sources, trace_id, not_found, chunks_retrieved, model_used} |

### Reranker Choice

| Question | Options | Selection |
|----------|---------|-----------|
| Which reranker? | Cohere Rerank API / Local cross-encoder / OpenRouter reranking | OpenRouter reranking (via existing client) |
| How should OpenRouter reranking work? | LLM scores each chunk / LLM selects top-N / Qdrant ANN score | Use rerank model provided by OpenRouter |
| Which OpenRouter rerank model? | cohere/rerank-v3.5 / cohere/rerank-4-fast | cohere/rerank-v3.5 |

**Note:** Research confirmed OpenRouter has a dedicated `/api/v1/rerank` endpoint (not a chat completion). `cohere/rerank-v3.5` at $0.001/search. Uses existing `OPENROUTER_API_KEY`.

### Not-Found Threshold

| Question | Options | Selection |
|----------|---------|-----------|
| What triggers not-found? | Reranker score cutoff / Zero results / LLM sentinel | Combine: reranker score cutoff (0.3) + LLM sentinel phrase |
| Score threshold? | 0.3 / 0.4 / 0.5 | 0.3 (default starting point) |

### Generation Model

| Question | Options | Selection |
|----------|---------|-----------|
| Which LLM for generation? | gpt-4o via openrouter_client / deepseek-chat via chunking_client | deepseek-v4-pro (user also requested chunking model → deepseek-v4-flash) |

**Note:** Research confirmed DeepSeek V4 model names: `deepseek-v4-pro` (1.6T params) and `deepseek-v4-flash` (284B params). `deepseek-chat` deprecated July 2026. Both use same `api.deepseek.com` base URL.

### Pipeline Depth

| Question | Options | Selection |
|----------|---------|-----------|
| How many chunks through pipeline? | Top 20 → rerank → filter → top 5 / Top 10 → top 3 / Top 20 → all passing | Top 20 → rerank → filter → top 5 to LLM |

### Audit Integration

| Question | Options | Selection |
|----------|---------|-----------|
| How to write audit record? | Inline (same request) / BackgroundTasks (after response) | Inline audit write |

### Auth & Role Access

| Question | Options | Selection |
|----------|---------|-----------|
| Which roles can query? | All roles / adviser + senior_adviser only | All roles (adviser, senior_adviser, compliance) |

### Session Management

| Question | Options | Selection |
|----------|---------|-----------|
| Session continuity? | Client passes optional session_id / New session per query | Client passes optional session_id, server validates |
| Session timeout? | 8 hours / 24 hours | 24 hours (user clarified: session close only sets end_time, logs preserved forever) |

### Query Enhancement

| Question | Options | Selection |
|----------|---------|-----------|
| Query enhancement? | Intent classification + rewrite / No enhancement / Rewrite only | Query rewrite only (no intent classification) |
| How to use rewritten query? | Rewritten for embedding + reranking / Rewritten for embedding, original for reranking | Rewritten for embedding, original for reranking |

---

## Claude's Discretion Items

- Exact system prompt wording (beyond constraints: cite-only-from-context, [N] markers, sentinel phrase, no training data)
- Retry logic for transient API failures
- Error messages for Qdrant unavailability
- Query rewrite prompt design

## Deferred Ideas

- SSE streaming — Phase 5 web UI
- Intent classification — analytics, future phase
- Multi-turn conversation context — single-turn for now
