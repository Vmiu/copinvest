# Architecture Patterns

**Domain:** Compliance-aware RAG assistant for HK investment advisers
**Researched:** 2026-04-29

## Recommended Architecture

The system has two distinct runtime modes: **ingestion** (offline, batch) and **query** (online, real-time). These share the vector store and database but are otherwise independent pipelines. A third surface — the Telegram bot — is a thin gateway that routes into the same query pipeline as the web UI.

```
┌─────────────────────────────────────────────────────────────────┐
│  INGESTION PIPELINE (offline / admin-triggered)                 │
│                                                                 │
│  Raw Docs (PDF/DOCX/XLSX)                                       │
│       ↓                                                         │
│  Document Loader (unstructured / Docling)                       │
│       ↓                                                         │
│  Chunker + Metadata Tagger                                      │
│  (sensitivity_tier, doc_type, source_id, allowed_roles[])       │
│       ↓                                                         │
│  Embedding Model (OpenAI text-embedding-3-small)                │
│       ↓                                                         │
│  ChromaDB (vectors + metadata)                                  │
│       ↓                                                         │
│  PostgreSQL doc_registry (doc metadata, ingestion audit)        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  QUERY PIPELINE (online / per-request)                          │
│                                                                 │
│  User Query (web UI or Telegram)                                │
│       ↓                                                         │
│  FastAPI Auth Middleware (JWT → user_id, roles[])               │
│       ↓                                                         │
│  RAG Service                                                     │
│    1. Embed query (OpenAI)                                      │
│    2. ChromaDB query with where={allowed_roles: {$contains:     │
│       user_role}} filter                                        │
│    3. Re-rank retrieved chunks (optional cross-encoder)         │
│    4. Build prompt with context + source citations              │
│    5. OpenAI GPT-4o generation                                  │
│       ↓                                                         │
│  Audit Logger → PostgreSQL rag_audit_log                        │
│       ↓                                                         │
│  Response with source attribution                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CHANNELS                                                       │
│                                                                 │
│  React Web UI ──────────────────────────────────────────────┐  │
│  (chat + brief generation + source panel)                   │  │
│                                                             ↓  │
│  Telegram Bot (aiogram 3.x webhook) ──────────────→ FastAPI    │
│  (quick queries, text-only responses)               /api/v1    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Ingestion Worker | Load, parse, chunk, embed, store docs | ChromaDB (write), PostgreSQL doc_registry (write) |
| ChromaDB | Vector storage + metadata-filtered retrieval | Ingestion Worker (write), RAG Service (read) |
| PostgreSQL | Audit log, doc registry, user/role store | RAG Service (write audit), Auth Service (read users) |
| Auth Middleware | Validate JWT, resolve user roles | PostgreSQL users table, all FastAPI routes |
| RAG Service | Orchestrate retrieval + generation | ChromaDB, OpenAI API, Audit Logger |
| Audit Logger | Write full trace per query | PostgreSQL rag_audit_log |
| FastAPI Backend | HTTP routing, auth, request/response | All backend services |
| React Frontend | Chat UI, brief generation, source display | FastAPI /api/v1 |
| Telegram Gateway | Receive webhook updates, format responses | FastAPI /api/v1 (same endpoints as web UI) |

## Data Flow

### Ingestion Flow

```
1. Admin drops file into /data/inbox/ (or uploads via admin API)
2. Ingestion worker picks up file
3. Parser extracts text + structure (unstructured for PDF/DOCX, pandas for XLSX)
4. Chunker splits into ~512-token chunks with overlap
5. Metadata tagger attaches:
   - source_id (UUID)
   - doc_type (factsheet | compliance | policy | template | data)
   - sensitivity_tier (1=public | 2=internal | 3=restricted | 4=confidential)
   - allowed_roles (array: ["adviser", "senior_adviser", "compliance"])
   - ingested_at, file_hash (for dedup)
6. Embedding model converts each chunk to vector
7. ChromaDB stores (vector, metadata, chunk_text)
8. PostgreSQL doc_registry records (source_id, filename, tier, ingested_at, chunk_count)
```

### Query Flow

```
1. User sends query (React UI via POST /api/v1/query or Telegram message)
2. FastAPI auth middleware validates JWT → extracts {user_id, role}
3. RAG Service:
   a. Embeds query text via OpenAI
   b. Queries ChromaDB with:
      - vector similarity search (top-k=20)
      - where filter: {allowed_roles: {$contains: user_role}}
   c. Re-ranks top-20 → top-5 by relevance
   d. Builds prompt: system instructions + retrieved chunks with [source_N] markers
   e. Calls OpenAI GPT-4o with prompt
   f. Parses response, maps [source_N] markers to doc metadata
4. Audit Logger writes to PostgreSQL:
   - trace_id, user_id, query_text
   - retrieved_chunks (JSONB: [{chunk_id, doc_id, score, snippet}])
   - prompt_sent (full prompt text)
   - llm_response (raw generation)
   - model_used, latency_ms, timestamp
5. Response returned: {answer, sources: [{title, doc_type, tier, chunk_snippet}]}
```

### Telegram Gateway Flow

```
1. Telegram sends POST to /webhook/telegram (HTTPS)
2. aiogram dispatcher parses Update object
3. Handler extracts message text + telegram_user_id
4. Gateway maps telegram_user_id → internal user_id (lookup table in PostgreSQL)
5. Calls same RAG Service as web UI (shared service layer)
6. Formats response as plain text (no rich HTML — Telegram markdown only)
7. Sends reply via Telegram Bot API
```

## FastAPI Backend Structure

```
backend/
├── main.py                    # App factory, lifespan (DB + ChromaDB init)
├── core/
│   ├── config.py              # Settings (pydantic-settings, env vars)
│   ├── database.py            # SQLAlchemy async engine + session factory
│   ├── security.py            # JWT decode, password hashing
│   └── dependencies.py        # FastAPI Depends: get_db, get_current_user
├── routers/
│   ├── query.py               # POST /api/v1/query
│   ├── briefs.py              # POST /api/v1/briefs (meeting brief generation)
│   ├── documents.py           # GET /api/v1/documents (list accessible docs)
│   ├── auth.py                # POST /api/v1/auth/token
│   ├── admin/
│   │   └── ingest.py          # POST /api/v1/admin/ingest (trigger ingestion)
│   └── webhook.py             # POST /webhook/telegram
├── services/
│   ├── rag_service.py         # Core: embed → retrieve → generate
│   ├── ingestion_service.py   # Parse → chunk → embed → store
│   ├── audit_service.py       # Write audit log entries
│   └── brief_service.py       # Meeting brief orchestration (wraps rag_service)
├── repositories/
│   ├── vector_repo.py         # ChromaDB queries (filtered retrieval)
│   ├── audit_repo.py          # PostgreSQL audit log writes/reads
│   ├── document_repo.py       # PostgreSQL doc_registry CRUD
│   └── user_repo.py           # PostgreSQL user/role lookups
├── models/
│   ├── user.py                # SQLAlchemy: users, roles
│   ├── audit_log.py           # SQLAlchemy: rag_audit_log
│   └── document.py            # SQLAlchemy: doc_registry
├── schemas/
│   ├── query.py               # QueryRequest, QueryResponse, SourceCitation
│   ├── brief.py               # BriefRequest, BriefResponse
│   └── auth.py                # TokenRequest, TokenResponse
└── workers/
    └── ingest_worker.py       # Standalone ingestion script (not a FastAPI route)
```

Key FastAPI patterns:
- `lifespan` context manager initializes ChromaDB client and DB connection pool at startup
- All routes use `Depends(get_current_user)` — no unauthenticated access to RAG endpoints
- `rag_service.py` is the only place that calls OpenAI and ChromaDB — keeps LLM logic isolated
- Telegram webhook handler calls `rag_service` directly, not via HTTP — avoids internal HTTP round-trip

## RBAC and Permission Filtering

### Sensitivity Tiers

| Tier | Label | Example Documents | Accessible By |
|------|-------|-------------------|---------------|
| 1 | Public | Product factsheets, general guides | All advisers |
| 2 | Internal | Meeting templates, process docs | All advisers |
| 3 | Restricted | Client-specific analysis, risk reports | Senior advisers + compliance |
| 4 | Confidential | Compliance investigations, regulatory filings | Compliance only |

### Implementation Pattern

Documents are tagged at ingestion with `allowed_roles` as a metadata array (ChromaDB metadata arrays, supported since Feb 2026). At query time, the user's role is injected as a `where` filter:

```python
# In vector_repo.py
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=20,
    where={"allowed_roles": {"$contains": user_role}},
    include=["documents", "metadatas", "distances"]
)
```

This is pre-retrieval filtering — the LLM never sees documents the user cannot access. Post-retrieval checks are not needed for this architecture because ChromaDB enforces the filter at the vector search layer.

Roles are stored in PostgreSQL and resolved at auth time. The JWT payload includes `role` so every request carries its own permission context without a DB lookup per query.

## Audit Log Schema

```sql
CREATE TABLE rag_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id        UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id         UUID NOT NULL REFERENCES users(id),
    channel         TEXT NOT NULL,          -- 'web' | 'telegram'
    query_text      TEXT NOT NULL,
    retrieved_chunks JSONB NOT NULL,        -- [{chunk_id, doc_id, score, snippet}]
    prompt_sent     TEXT NOT NULL,
    llm_response    TEXT NOT NULL,
    model_used      TEXT NOT NULL,
    latency_ms      INTEGER,
    adviser_edited  BOOLEAN DEFAULT FALSE,  -- did adviser modify the output?
    adviser_action  TEXT,                   -- 'sent' | 'discarded' | 'saved'
    metadata        JSONB
);

CREATE INDEX idx_audit_user_id ON rag_audit_log(user_id);
CREATE INDEX idx_audit_created_at ON rag_audit_log(created_at);
CREATE INDEX idx_audit_trace_id ON rag_audit_log(trace_id);
```

The `adviser_edited` and `adviser_action` fields are critical for SFC compliance — they record whether the adviser used, modified, or discarded the AI-generated output. The React UI must send a follow-up PATCH to record this action.

## Patterns to Follow

### Pattern 1: Pre-Retrieval Permission Filtering
**What:** Inject user role as a ChromaDB `where` filter before vector search
**When:** Every query — no exceptions
**Why:** Ensures the LLM context window never contains documents the user cannot access. Post-retrieval filtering is a fallback, not a substitute.

### Pattern 2: Immutable Audit Log
**What:** Audit log rows are INSERT-only. No UPDATE or DELETE.
**When:** Every query, every generation
**Why:** SFC compliance requires tamper-evident records. Use PostgreSQL row-level security to prevent application-layer deletes.

### Pattern 3: Source Attribution in Prompt
**What:** Each retrieved chunk is prefixed with `[source_N]` in the prompt. The system instruction requires the LLM to cite sources inline.
**When:** All generation calls
**Why:** Prevents hallucination of advice not grounded in approved documents. Citations are parsed from the response and returned as structured metadata.

### Pattern 4: Shared Service Layer for All Channels
**What:** Telegram gateway and React UI both call `rag_service.py` directly — not via internal HTTP
**When:** Any new channel added
**Why:** Avoids duplicating RAG logic. Audit logging happens in the service layer, so all channels are automatically audited.

### Pattern 5: Async Throughout
**What:** All FastAPI routes, service calls, and DB operations use `async/await`
**When:** All I/O operations (ChromaDB, OpenAI, PostgreSQL)
**Why:** OpenAI API calls can take 2-10 seconds. Blocking the event loop would serialize all requests.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Post-Retrieval Permission Filtering
**What:** Retrieve all documents, then filter by role after
**Why bad:** The LLM may still see restricted content in the context window before filtering. Also wastes tokens and latency.
**Instead:** Always filter at the ChromaDB query layer with `where` metadata filters.

### Anti-Pattern 2: Storing Full Prompt in Application Memory Only
**What:** Keeping the prompt in memory and only logging a summary
**Why bad:** Fails SFC audit requirements. If the system is restarted, the trace is lost.
**Instead:** Write the full `prompt_sent` text to PostgreSQL before calling the LLM.

### Anti-Pattern 3: Telegram Bot as Separate Backend
**What:** Running a separate Python process for the Telegram bot with its own RAG logic
**Why bad:** Duplicates ingestion, retrieval, and audit logic. Telegram interactions won't appear in the unified audit log.
**Instead:** Telegram bot is a webhook endpoint in the same FastAPI app, calling the shared service layer.

### Anti-Pattern 4: Chunking Without Metadata
**What:** Storing chunks in ChromaDB without source metadata
**Why bad:** Cannot implement permission filtering. Cannot generate source citations. Cannot trace which document produced which answer.
**Instead:** Every chunk must carry `source_id`, `doc_type`, `sensitivity_tier`, `allowed_roles`, `page_number` (for PDFs).

### Anti-Pattern 5: Synchronous Ingestion in Request Handler
**What:** Triggering document ingestion inside a FastAPI request handler and waiting for it
**Why bad:** Ingestion of a large PDF can take 30-120 seconds. This will timeout.
**Instead:** Ingestion is a background worker (separate script or Celery task). The API endpoint just enqueues the job and returns immediately.

## Scalability Considerations

| Concern | At prototype (5 users) | At small firm (50 users) | At scale (500+ users) |
|---------|----------------------|--------------------------|----------------------|
| Vector store | ChromaDB local file | ChromaDB server mode | Migrate to pgvector or Weaviate |
| LLM calls | Direct OpenAI API | Direct OpenAI API + rate limit handling | OpenAI with org-level rate limits or Azure OpenAI |
| Audit log | PostgreSQL single table | PostgreSQL + indexes | Partition by month, add read replica |
| Auth | Simple JWT + PostgreSQL | Same | Add SSO/SAML integration |
| Ingestion | Manual trigger | Scheduled batch | Event-driven (file watcher or S3 trigger) |
| Deployment | Single VM | Single VM or small VPS | Container + managed DB |

For v1 (prototype), ChromaDB in local persistent mode on a single VM is sufficient. The architecture is designed so ChromaDB can be swapped for pgvector without changing the service layer — `vector_repo.py` is the only file that knows about the vector store implementation.

## Suggested Build Order

Dependencies drive this order — each phase unblocks the next.

```
Phase 1: Data Foundation
  → PostgreSQL schema (users, doc_registry, audit_log)
  → ChromaDB setup with metadata schema
  → Auth middleware (JWT)
  Unblocks: everything else

Phase 2: Ingestion Pipeline
  → Document loaders (PDF, DOCX, XLSX)
  → Chunker + metadata tagger
  → Embedding + ChromaDB write
  Unblocks: RAG retrieval (needs data in the store)

Phase 3: RAG Query Pipeline
  → vector_repo.py with permission filtering
  → rag_service.py (embed → retrieve → generate)
  → audit_service.py
  → FastAPI /api/v1/query endpoint
  Unblocks: all user-facing surfaces

Phase 4: React Web UI
  → Chat interface with streaming
  → Source attribution panel
  → Adviser action tracking (edited/sent/discarded)
  Unblocks: primary user workflow

Phase 5: Brief Generation
  → brief_service.py (structured prompt for meeting briefs)
  → /api/v1/briefs endpoint
  → Brief UI in React
  Depends on: Phase 3 (RAG pipeline)

Phase 6: Telegram Gateway
  → aiogram webhook setup
  → Telegram user → internal user mapping
  → Webhook endpoint in FastAPI
  Depends on: Phase 3 (RAG pipeline)
  Can be parallel with: Phase 4 (React UI)
```

The Telegram gateway (Phase 6) can be built in parallel with the React UI (Phase 4) because both depend only on the RAG service layer being complete. Brief generation (Phase 5) is a specialization of the query pipeline, not a new component.

## Sources

- [Permissions, Security, and Compliance in RAG Pipelines](https://unified.to/blog/permissions_security_and_compliance_in_rag_pipelines) — MEDIUM confidence (WebSearch, March 2026)
- [Implementing Granular Access Control in RAG Applications](https://willrodbard.com/2025/09/11/implementing-granular-access-control-in-rag-applications/) — MEDIUM confidence (WebSearch, Sept 2025)
- [ChromaDB Metadata Filtering — Official Docs](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) — HIGH confidence (official docs)
- [ChromaDB Metadata Arrays Changelog](https://www.trychroma.com/changelog/metadata-arrays) — HIGH confidence (official changelog, Feb 2026)
- [Implementing Authorization in RAG-Based AI Systems — Cerbos](https://docs.cerbos.dev/cerbos/0.42.0/recipes/ai/rag-authorization/index.html) — HIGH confidence (official docs)
- [RAG Engineering Part 6: Security, Compliance, and Cost Optimization](https://medium.com/@adnansattar09/rag-engineering-part-6-security-compliance-and-cost-optimization-56b65f11a56a) — MEDIUM confidence (WebSearch, Jan 2026)
- [FastAPI Webhooks & Aiogram: A Winning Combo](https://wiki.fremontleaf.org/official-files/fastapi-webhooks-and-aiogram-a-winning-combo-1764797230) — MEDIUM confidence (WebSearch)
- [Build a Smarter Telegram Bot: Integrating a RAG Pipeline](https://www.endpointdev.com/blog/2025/12/telegram-bot-rag-pipeline/) — MEDIUM confidence (WebSearch, Dec 2025)
- [Audit Logging: Tracking Which Documents Answered Which Queries](https://theneuralbase.com/rag-fundamentals/learn/advanced/audit-logging-tracking-which-documents-answered-which-queries/) — MEDIUM confidence (WebSearch)
- [Production-Ready FastAPI Project Structure (2026 Guide)](https://dev.to/thesius_code_7a136ae718b7/production-ready-fastapi-project-structure-2026-guide-b1g) — MEDIUM confidence (WebSearch, Mar 2026)
- [LangChain UnstructuredPDFLoader — Official Docs](https://python.langchain.com/docs/integrations/document_loaders/unstructured_pdfloader/) — HIGH confidence (official docs)
- [LangChain Docling Integration — Official Docs](https://python.langchain.com/docs/integrations/document_loaders/docling) — HIGH confidence (official docs)
- [MUI X Sources & Citations Component](https://mui.com/x/react-chat/display/message-parts/sources-and-citations/) — HIGH confidence (official docs)
