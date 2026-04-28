# Technology Stack

**Project:** CopInvest — Compliance-aware RAG assistant for HK investment advisers
**Researched:** 2026-04-29
**Overall confidence:** HIGH (all major choices verified against current docs/releases)

---

## Recommended Stack

### Core RAG Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LlamaIndex | 0.12.x (latest: 0.12.46) | RAG orchestration, retrieval, query engine | Purpose-built for RAG; first-class metadata filtering, chunking strategies, and query engine abstractions. Outperforms LangChain on retrieval accuracy for document Q&A. Active 2025 release cadence. |
| openai | >=1.68.0 | LLM completions + embeddings | Official SDK, async-native (`AsyncOpenAI`), streaming via `.stream()` context manager. |

**Why LlamaIndex over LangChain:** LangChain is a general-purpose LLM orchestration framework — better when agents + tool use are the core concern. CopInvest is a RAG-first product (document Q&A, meeting briefs, source attribution). LlamaIndex's `VectorStoreIndex`, `MetadataFilters`, and `QueryEngine` abstractions map directly to this use case with less boilerplate. LangChain's LCEL adds complexity without benefit here.

**Why not custom RAG:** LlamaIndex handles chunking, embedding, retrieval, re-ranking, and source attribution out of the box. Custom pipelines require rebuilding all of this and are harder to maintain.

### Vector Store

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Qdrant | qdrant-client 1.17.x | Vector storage + metadata-filtered retrieval | Pre-filtering architecture (filters applied before ANN search, not post-hoc) is critical for sensitivity-tier RBAC. `must` filter on `sensitivity_tier` payload field enforces access control at the DB layer. Rust-based, production-hardened, runs as a single Docker container. |

**Why Qdrant over ChromaDB:** ChromaDB is excellent for prototyping but lacks production-hardened filtering performance and has no distributed mode. For this project, sensitivity-tier filtering is a first-class requirement — Qdrant's pre-filtering ensures unauthorized documents are never retrieved, not just filtered post-retrieval. This is the correct security model.

**Why Qdrant over pgvector:** pgvector's SQL-based filtering is expressive, but adds a Postgres dependency. Qdrant runs standalone as a Docker container, keeping the deployment simpler for a single-VM prototype. pgvector is the right choice if Postgres is already in the stack; it isn't here.

**Why Qdrant over FAISS:** FAISS is an in-process library with no built-in metadata filtering, persistence, or server mode. It requires custom wrappers for everything CopInvest needs. Not appropriate.

### Embedding Model

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| text-embedding-3-small | current | Document + query embeddings | $0.02/1M tokens vs $0.13/1M for `large` — 6.5x cheaper with only ~2-3 MTEB point difference. For a small internal corpus (factsheets, compliance docs, meeting templates), the quality delta is not meaningful. 1536 dimensions, supports Matryoshka dimension reduction. |

### LLM Model

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| gpt-4o | current | Response generation | Strong instruction-following for structured outputs (meeting briefs, follow-up notes). Constrained by system prompt to cite sources only from retrieved context — no hallucinated advice. |

### Backend Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.128.x | REST API + SSE streaming | Async-native, `StreamingResponse` for token streaming to the React UI, `BackgroundTasks` for non-blocking audit log writes. Auto-generates OpenAPI docs. Pydantic v2 validation built in. |
| SQLAlchemy | 2.0.x | ORM for audit log + user/doc metadata | Async session (`AsyncSession`) with `async_sessionmaker`. Event hooks for audit trail. Declarative models. |
| SQLite (dev) / PostgreSQL (prod) | — | Audit log + user/permission storage | SQLite for local dev (zero config), Postgres for cloud VM. SQLAlchemy abstracts the difference. |
| Alembic | latest | DB migrations | Standard SQLAlchemy migration tool. |

### Document Ingestion

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| docling | 2.x (latest: 2.91.0) | PDF, Word (.docx), Excel (.xlsx) parsing | IBM-backed, purpose-built for AI/RAG pipelines. Handles complex PDFs (tables, figures, multi-column layouts) with high fidelity. Exports to structured markdown. Actively developed — v2.91.0 as of April 2026. Single library covers all three required formats. |

**Why docling over unstructured:** `unstructured` is battle-tested but has a heavier dependency footprint and a managed API tier that adds cost. `docling` is fully local, lighter, and has better structured output for RAG (preserves table structure, section hierarchy). For a single-firm prototype with internal docs, docling is the cleaner choice.

**Why not pypdf alone:** pypdf handles PDF text extraction only. CopInvest requires Word and Excel too. docling covers all three.

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.x | Web UI framework | Specified in project constraints. |
| @assistant-ui/react | 0.12.x (latest: 0.12.26) | Chat UI with streaming | Purpose-built for AI chat UIs. Handles streaming token rendering, message threads, tool call display, and source citation rendering. Active release cadence (0.12.26 published April 2026). Avoids building a custom streaming chat component from scratch. |
| Tailwind CSS | 3.x | Styling | Utility-first, pairs well with assistant-ui components. |

**Why @assistant-ui/react over building custom:** Streaming chat UIs have non-trivial edge cases (partial token rendering, abort handling, scroll-to-bottom, message state). assistant-ui solves these. It integrates with the Vercel AI SDK data stream format, which FastAPI can emit via SSE.

### Telegram Bot

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-telegram-bot | 22.x (latest: 22.7) | Telegram bot for quick mobile queries | Fully async (asyncio + httpx), `ConversationHandler` for multi-step flows, built-in webhook runner (`Application.run_webhook()`). The de-facto standard Python Telegram library. |

**Integration pattern:** The Telegram bot runs as a separate async process (or alongside FastAPI via webhook). It calls the same internal RAG service layer as the web API — no duplicated logic. Audit logging applies to Telegram queries identically.

### Audit Logging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLAlchemy AsyncSession | 2.0.x | Audit record persistence | Dedicated `AuditLog` table. Written via `BackgroundTasks` in FastAPI so it never blocks the response. |
| structlog | latest | Structured application logging | JSON-structured logs for operational observability. Separate from the compliance audit trail (which lives in the DB). |

**Audit record schema (minimum):**
- `id`, `timestamp`, `user_id`, `channel` (web/telegram)
- `query_text`, `retrieved_doc_ids` (JSON array), `sensitivity_tier_accessed`
- `generated_response` (full text), `adviser_edited` (bool), `final_response`
- `model_used`, `prompt_tokens`, `completion_tokens`

This schema supports SFC audit requirements: every query → retrieved docs → generated output → adviser action is traceable.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| RAG framework | LlamaIndex | LangChain | LangChain is agent-first; heavier for pure RAG. LlamaIndex has better retrieval abstractions for document Q&A. |
| RAG framework | LlamaIndex | Custom pipeline | Rebuilds chunking, embedding, retrieval, re-ranking from scratch. Maintenance burden without benefit. |
| Vector store | Qdrant | ChromaDB | ChromaDB lacks production-hardened pre-filtering. Post-retrieval filtering is wrong security model for RBAC. |
| Vector store | Qdrant | FAISS | No server mode, no metadata filtering, no persistence. Requires custom wrappers for everything. |
| Vector store | Qdrant | pgvector | Adds Postgres dependency. Qdrant is simpler for single-VM deployment without existing Postgres. |
| Embedding model | text-embedding-3-small | text-embedding-3-large | 6.5x more expensive ($0.13 vs $0.02/1M tokens) for ~2-3 MTEB point gain. Not justified for small internal corpus. |
| Document ingestion | docling | unstructured | Heavier deps, managed API tier adds cost. docling is fully local and has better structured output for RAG. |
| Document ingestion | docling | pypdf | PDF-only. CopInvest requires Word and Excel too. |
| Chat UI | @assistant-ui/react | Custom component | Streaming chat has non-trivial edge cases. assistant-ui solves them. |
| Telegram | python-telegram-bot | aiogram | Both are async. python-telegram-bot has larger community, better docs, and ConversationHandler is well-tested. |

---

## Installation

```bash
# Backend core
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] alembic aiosqlite asyncpg

# RAG stack
pip install llama-index llama-index-vector-stores-qdrant qdrant-client openai

# Document ingestion
pip install docling

# Telegram bot
pip install python-telegram-bot

# Observability
pip install structlog

# Dev
pip install pytest pytest-asyncio httpx
```

```bash
# Frontend
npm install @assistant-ui/react react react-dom
npm install -D tailwindcss
```

---

## Sources

- LlamaIndex Python docs: https://developers.llamaindex.ai/python/
- LlamaIndex releases: https://github.com/run-llama/llama_index/releases (v0.12.46 latest as of July 2025)
- Qdrant filtering docs: https://qdrant.tech/documentation/search/filtering/
- Qdrant Python client: https://python-client.qdrant.tech/ (v1.17.1 latest)
- ChromaDB cookbook (metadata filtering): https://cookbook.chromadb.dev/core/filters
- OpenAI Python SDK: https://github.com/openai/openai-python (v1.68.0+)
- OpenAI embedding pricing: https://tokenmix.ai/blog/openai-embedding-pricing
- FastAPI releases: https://github.com/fastapi/fastapi/releases (v0.128.1 latest)
- docling: https://github.com/docling-project/docling (v2.91.0 latest)
- @assistant-ui/react: https://www.npmjs.com/package/@assistant-ui/react (v0.12.26 latest)
- python-telegram-bot: https://docs.python-telegram-bot.org/en/v22.7/ (v22.7 latest)
- LangChain vs LlamaIndex 2026: https://dev.to/lycore/langchain-vs-llamaindex-in-2026-what-we-actually-use-and-why-52eb
- Vector DB comparison 2026: https://4xxi.com/articles/vector-database-comparison
- Qdrant RBAC pattern: https://dev.to/quamernasim/enhancing-data-security-with-role-based-access-control-of-qdrant-vector-database-1ii4
- FastAPI audit logging patterns: https://blog.greeden.me/en/2026/03/17/a-practical-introduction-to-audit-log-design-in-fastapi-design-and-implementation-patterns-for-safely-recording-who-did-what-and-when/
