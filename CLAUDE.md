<!-- GSD:project-start source:PROJECT.md -->
## Project

**CopInvest**

A GenAI assistant for investment advisers in Hong Kong that uses retrieval-augmented generation (RAG) over approved internal content to prepare meeting briefs, summarize product information, and draft compliant follow-up notes. It replaces the manual "tab-switching across CRM + portfolio system + Word + email" workflow with a single assistant that synthesizes context and generates first drafts for adviser review.

**Core Value:** Advisers can ask a question about a client, product, or meeting and get an accurate, source-attributed answer drawn only from approved internal documents — with every interaction fully auditable.

### Constraints

- **Tech stack**: Python (FastAPI) backend, React frontend, OpenAI for LLM
- **Vector store**: ChromaDB or FAISS for embeddings with metadata-based permission filtering
- **Deployment**: Local or single cloud VM — no container orchestration for v1
- **Document formats**: Must handle PDF, Word (.docx), and Excel/CSV ingestion
- **Compliance**: All generated content must cite source documents; no hallucinated advice
- **Auditability**: Full trace from query → retrieval → generation → adviser action
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core RAG Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LlamaIndex | 0.12.x (latest: 0.12.46) | RAG orchestration, retrieval, query engine | Purpose-built for RAG; first-class metadata filtering, chunking strategies, and query engine abstractions. Outperforms LangChain on retrieval accuracy for document Q&A. Active 2025 release cadence. |
| openai | >=1.68.0 | LLM completions + embeddings | Official SDK, async-native (`AsyncOpenAI`), streaming via `.stream()` context manager. |
### Vector Store
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Qdrant | qdrant-client 1.17.x | Vector storage + metadata-filtered retrieval | Pre-filtering architecture (filters applied before ANN search, not post-hoc) is critical for sensitivity-tier RBAC. `must` filter on `sensitivity_tier` payload field enforces access control at the DB layer. Rust-based, production-hardened, runs as a single Docker container. |
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
### Frontend
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.x | Web UI framework | Specified in project constraints. |
| @assistant-ui/react | 0.12.x (latest: 0.12.26) | Chat UI with streaming | Purpose-built for AI chat UIs. Handles streaming token rendering, message threads, tool call display, and source citation rendering. Active release cadence (0.12.26 published April 2026). Avoids building a custom streaming chat component from scratch. |
| Tailwind CSS | 3.x | Styling | Utility-first, pairs well with assistant-ui components. |
### Telegram Bot
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-telegram-bot | 22.x (latest: 22.7) | Telegram bot for quick mobile queries | Fully async (asyncio + httpx), `ConversationHandler` for multi-step flows, built-in webhook runner (`Application.run_webhook()`). The de-facto standard Python Telegram library. |
### Audit Logging
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLAlchemy AsyncSession | 2.0.x | Audit record persistence | Dedicated `AuditLog` table. Written via `BackgroundTasks` in FastAPI so it never blocks the response. |
| structlog | latest | Structured application logging | JSON-structured logs for operational observability. Separate from the compliance audit trail (which lives in the DB). |
- `id`, `timestamp`, `user_id`, `channel` (web/telegram)
- `query_text`, `retrieved_doc_ids` (JSON array), `sensitivity_tier_accessed`
- `generated_response` (full text), `adviser_edited` (bool), `final_response`
- `model_used`, `prompt_tokens`, `completion_tokens`
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
## Installation
# Backend core
# RAG stack
# Document ingestion
# Telegram bot
# Observability
# Dev
# Frontend
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### Python Environment
- **Always use `uv`** for Python environment management. Never use `pip`, `python -m venv`, or bare `python`.
- Create venv: `uv venv`
- Install deps: `uv pip install -e ".[dev]"`
- Run Python code: `uv run python ...`
- Run tests: `uv run pytest tests/ -q`
- Run any Python tool: `uv run <tool>` (e.g., `uv run alembic`, `uv run uvicorn`)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
