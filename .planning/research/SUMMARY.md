# Research Summary

**Project:** CopInvest — Compliance-aware RAG assistant for HK investment advisers
**Synthesized:** 2026-04-29
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Recommended Stack (Reconciled)

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| RAG Framework | LlamaIndex | 0.12.x | Purpose-built for document Q&A; first-class metadata filtering and query engines |
| Vector Store | Qdrant | qdrant-client 1.17.x | Pre-filtering architecture enforces RBAC at DB layer before ANN search — correct security model |
| Embeddings | text-embedding-3-small | current | $0.02/1M tokens; sufficient quality for small internal corpus |
| LLM | gpt-4o (pinned version) | current | Strong instruction-following for structured outputs; pin version for audit trail |
| Backend | FastAPI | 0.128.x | Async-native, SSE streaming, BackgroundTasks for audit writes |
| ORM | SQLAlchemy | 2.0.x | Async sessions, declarative models, Alembic migrations |
| DB | SQLite (dev) / PostgreSQL (prod) | — | Audit log + user/role storage |
| Doc Ingestion | docling | 2.91.x | Handles PDF/Word/Excel with table extraction; single library for all formats |
| Frontend | React + @assistant-ui/react | 18.x / 0.12.x | Streaming chat UI with source citations out of the box |
| Telegram | python-telegram-bot | 22.7 | Async, webhook support, ConversationHandler |
| Logging | structlog | latest | Structured JSON logs for operational observability |

**Key reconciliation:** Architecture research used ChromaDB; Stack research recommended Qdrant. Pitfalls research confirmed ChromaDB's post-retrieval filtering is a security concern for RBAC. **Decision: Use Qdrant** — its pre-filtering ensures unauthorized documents are never retrieved, which is the correct model for sensitivity-tiered access.

---

## Table Stakes Features

1. Document Q&A with source attribution (regulatory requirement per SFC 24EC55)
2. Full audit trail (query → retrieval → generation → adviser action)
3. Role-based document access via sensitivity tiers (pre-retrieval filtering)
4. Meeting brief generation from internal docs
5. Compliant follow-up note drafting
6. Human-in-the-loop review (SFC mandates human oversight)
7. "No answer" discipline (refuse to hallucinate; say "not found in approved docs")

---

## Critical Pitfalls to Address Early

| # | Pitfall | Phase | Prevention |
|---|---------|-------|------------|
| 1 | Permission filtering applied post-retrieval (data leakage) | Phase 1 | Hard `where` filter in every Qdrant query; test with restricted docs |
| 2 | Hallucinated financial advice presented as sourced | Phase 1 | Strict system prompt; programmatic citation extraction; confidence thresholds |
| 3 | Audit trail gaps that fail regulatory review | Phase 1 | Design full audit schema before first query; immutable append-only records |
| 4 | PDF parsing silently drops content (tables, footnotes) | Phase 1 | Use docling; spot-check extraction quality; log parsing warnings |
| 5 | Telegram bot token exposure | Phase 1 | Secrets manager from first commit; webhook secret validation |

---

## Architecture Summary

Two independent pipelines sharing Qdrant + PostgreSQL:

```
INGESTION (offline):  Raw Docs → docling → Chunker + Metadata Tagger → Embeddings → Qdrant
QUERY (online):       User Query → Auth → Qdrant (filtered) → Rerank → LLM → Audit Log → Response
CHANNELS:             React Web UI ─┐
                      Telegram Bot ──┼──→ Shared RAG Service Layer → FastAPI /api/v1
```

**Build order (dependency-driven):**
1. Data Foundation — Qdrant schema, PostgreSQL (users, audit_log, doc_registry), Auth middleware
2. Ingestion Pipeline — docling parsing, chunking, metadata tagging, embedding, Qdrant write
3. RAG Query Pipeline — filtered retrieval, generation, audit logging, /api/v1/query endpoint
4. React Web UI — chat interface, source panel, adviser action tracking
5. Brief Generation — structured prompts for meeting briefs, /api/v1/briefs endpoint
6. Telegram Gateway — webhook endpoint, user mapping, text-only responses

Phases 4-6 can partially parallelize once Phase 3 is complete.

---

## HK SFC Regulatory Context

SFC Circular 24EC55 (Nov 2024) sets the compliance floor:
- Human oversight required before AI output reaches clients
- Full recordkeeping of AI-assisted interactions (likely 7-year retention)
- Senior management accountability for AI use
- Due diligence documentation on third-party AI providers (OpenAI)

**Implication:** Audit trail and human-review workflow are not optional enhancements — they are the minimum bar for SFC-licensed advisers.

---

## Key Design Decisions (from research)

| Decision | Rationale |
|----------|-----------|
| Qdrant over ChromaDB | Pre-filtering architecture is correct security model for RBAC |
| LlamaIndex over LangChain | RAG-first product; LlamaIndex has better retrieval abstractions |
| docling over unstructured | Lighter, fully local, better structured output for financial docs |
| Pin OpenAI model version | Audit trail must record exact model; unversioned alias causes drift |
| Telegram scoped to read-only Q&A | Draft generation via Telegram creates compliance risk (no review step) |
| Immutable audit log (INSERT-only) | SFC requires tamper-evident records |

---

## Open Questions for Planning

1. Chunking strategy for financial tables vs narrative text — needs empirical testing
2. SFC audit retention period (likely 7 years) — confirm from primary source
3. OpenAI data residency (US-based) — any HK PDPO implications?
4. Qdrant deployment mode — Docker container vs in-process for prototype?

---

*Synthesized from 4 parallel research agents on 2026-04-29*
