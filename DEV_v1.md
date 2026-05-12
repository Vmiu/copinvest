# CopInvest — Implemented Features (v1)

## Backend

### API Endpoints

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| POST | `/api/v1/auth/token` | — | Login, returns JWT |
| GET | `/api/v1/auth/me` | any | Current user info |
| POST | `/api/v1/query` | adviser, senior_adviser, compliance | RAG query pipeline |
| POST | `/api/v1/ingest` | compliance | Upload + ingest document |
| GET | `/api/v1/documents` | compliance | List ingested documents |
| GET | `/api/v1/audit` | compliance | List audit logs (paginated, filterable) |
| GET | `/api/v1/audit/{trace_id}` | compliance | Full trace detail |

### RAG Pipeline (`POST /query`)

1. **Session management** — get or create session (24h timeout)
2. **Audit record** — created immediately, survives pipeline failures
3. **Query rewrite** — DeepSeek V4 Flash rewrites query for better retrieval
4. **Embedding** — Voyage AI `voyage-finance-2` (1024 dims) via HTTP
5. **RBAC retrieval** — Qdrant pre-filters on `allowed_roles` + `sensitivity_tier` before ANN search
6. **Reranking** — Cohere `rerank-v3.5` via OpenRouter (threshold 0.3, top 5)
7. **Generation** — DeepSeek V4 Pro with inline `[N]` citations, constrained to retrieved context
8. **Audit update** — stores chunks (source, index, tier, section, text), prompt, response, tokens

### Document Ingestion (`POST /ingest`)

- **PDF** — rendered as images, extracted with Mistral Medium 3.5 vision via OpenRouter
- **DOCX / XLSX / CSV** — parsed with docling
- **Chunking** — semantic chunking via DeepSeek V4 Flash with page overlap context
- **Embedding** — Voyage AI, upserted to Qdrant with metadata payload
- **Registry** — document record saved to SQLite (write-then-replace atomicity on re-ingest)

### Data Models

**SQLite tables** (async SQLAlchemy + Alembic migrations)

- `users` — id, email, hashed_password, role (adviser / senior_adviser / compliance)
- `sessions` — id, user_id, start_time, last_activity
- `audit_logs` — full lifecycle trace per query:
  - **Identity**: user_id, session_id, timestamp, channel (web / telegram)
  - **Query**: query_text, rewritten_query
  - **Retrieval**: retrieved_chunks (JSON — source_id, chunk_index, section_title, sensitivity_tier, text), sensitivity_tier_accessed, chunks_passed_rerank
  - **Generation**: prompt_sent, llm_response, model_used, prompt_tokens, completion_tokens, not_found
  - **Adviser action**: adviser_action (approved / edited / discarded), adviser_edited, final_response
  - **Status**: received → retrieved → generated → completed / error
- `document_records` — document_id, filename, doc_type, sensitivity_tier, chunk_count, ingested_at, ingested_by

**Qdrant collection** `documents` — 1024-dim cosine, payload indexes on `allowed_roles`, `sensitivity_tier`, `source_id`

### Auth & Security

- JWT HS256, 24h expiry
- Role-based access via `require_role` dependency
- Passwords hashed with pwdlib/bcrypt
- RBAC enforced at vector DB layer (pre-filter, not post-filter)

---

## Frontend

### Pages

**Login** (`/login` — shown when unauthenticated)
- Hardcoded compliance user: `carol@copinvest.hk`
- POSTs to `/api/v1/auth/token`, stores JWT in localStorage
- Redirects to app on success

**Audit Log** (`/audit`)
- Paginated table (25/page) of all query traces
- Filters: date range, user ID, session ID
- Badges: channel (web/telegram), status, adviser action
- Click row → TraceInspector

**Trace Inspector** (`/audit/:trace_id`)
- Collapsible sections: Query, Retrieved Chunks, Prompt Sent, LLM Response, Adviser Action, Metadata
- Retrieved Chunks: one card per chunk showing source, chunk index, sensitivity tier, section title, full text
- Metadata: model, prompt/completion tokens, session ID, chunks passed rerank

**Document Registry** (`/documents`)
- Table of all ingested documents
- Filter by sensitivity tier (Public / Internal / Restricted / Confidential)
- Sortable by ingested date

**Ingest Document** (`/ingest`)
- File upload (PDF, DOCX, XLSX)
- Sensitivity tier selector
- Shows result: document ID, chunk count, warnings

### Infrastructure

- Axios client with auto-injected Bearer token from localStorage
- Dark theme (shadcn CSS vars + Tailwind, `.dark` on `<html>`)
- Sidebar with Sign out button
- React Router with auth gate (token check before rendering app)

---

## External Services

| Service | Model / Version | Purpose |
|---------|----------------|---------|
| DeepSeek | V4 Flash | Query rewrite, chunking |
| DeepSeek | V4 Pro | Answer generation |
| Mistral | Medium 3.5 (via OpenRouter) | PDF vision parsing |
| Cohere | rerank-v3.5 (via OpenRouter) | Chunk reranking |
| Voyage AI | voyage-finance-2 | Embeddings |
| Qdrant | localhost:6333 | Vector store |
| SQLite | — | Audit log, users, documents |
