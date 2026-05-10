# CopInvest

## What This Is

A compliance-aware RAG assistant for investment advisers in Hong Kong. Advisers query it via Telegram to get source-attributed answers from approved internal documents (PDFs, Word, Excel). A React web dashboard gives compliance officers full audit trail visibility and document management. Every interaction is fully auditable from query through retrieval, generation, and adviser action.

## Core Value

Advisers can ask a question and get an accurate, source-attributed answer drawn only from approved internal documents — with every interaction fully auditable.

## Requirements

### Validated

- ✓ RAG-powered Q&A over internal documents (PDFs, Word, Excel/CSV) — v1.0
- ✓ Sensitivity-tiered document access (role-based permissions on retrieval) — v1.0
- ✓ Full audit trail (every query, retrieved docs, generated output, adviser edits) — v1.0
- ✓ Source attribution on all generated responses — v1.0
- ✓ Telegram bot as primary adviser interface — v1.0 (promoted from secondary)
- ✓ React web UI as audit/admin dashboard — v1.0 (scoped down from primary interface)

### Active

- [ ] Meeting brief generation from client context and internal docs (BRIEF-01, BRIEF-02)
- [ ] Compliant follow-up note drafting (FOLLOW-01, FOLLOW-02)
- [ ] Immutable append-only audit records with 7-year retention (AUDIT-V2-01, AUDIT-V2-03)
- [ ] Adviser edit tracking with diff between AI draft and final sent version (AUDIT-V2-02)
- [ ] Compliance guardrail layer — detect specific investment advice, price targets (COMP-01)
- [ ] Faithfulness scoring — verify each claim traces to a retrieved chunk (COMP-02)

### Out of Scope

- Multi-tenant SaaS — personal prototype, single-firm architecture
- Real-time portfolio data feeds — internal static exports only
- Mobile native app — web + Telegram covers mobile access
- Graph database (Neo4j) — vector-first is sufficient; graph layer deferred
- CRM write-back — read-only for now
- Multi-LLM provider switching — provider mix already evolved (DeepSeek, Voyage AI, cohere)
- Autonomous advice delivery — SFC requires human review; never auto-send AI output to clients
- Open-ended internet search — mixing internal + external content destroys compliance boundary

## Context

**Regulatory environment:** Hong Kong SFC guidelines govern how investment advice is documented. The audit trail must demonstrate that advice was derived from approved materials.

**Current state (v1.0):** ~35,800 lines across Python backend and React frontend. Stack evolved from the original OpenAI-only plan: DeepSeek V4 for generation, Voyage AI for embeddings, cohere rerank-v3.5 for reranking, Qdrant for vector storage. docling handles PDF/Word/Excel parsing. Telegram is the primary adviser interface; React web UI is audit/admin only.

**Target users:** Small group of advisers at a single firm. Architecture is clean enough to scale but doesn't need multi-tenancy now.

## Constraints

- **Tech stack**: Python (FastAPI) backend, React frontend
- **LLM**: DeepSeek V4 Pro for generation, DeepSeek V4 Flash for query rewriting
- **Embeddings**: Voyage AI (text-embedding-3-small was original plan; Voyage AI adopted during Phase 3)
- **Reranking**: cohere rerank-v3.5 via OpenRouter
- **Vector store**: Qdrant (pre-filtering enforces RBAC at DB layer)
- **Deployment**: Local or single cloud VM — no container orchestration for v1
- **Document formats**: PDF, Word (.docx), Excel/CSV via docling
- **Compliance**: All generated content must cite source documents; no hallucinated advice
- **Auditability**: Full trace from query → retrieval → generation → adviser action

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Qdrant over ChromaDB/FAISS | Pre-filtering enforces RBAC at DB layer — correct security model | ✓ Good |
| Audit trail in Phase 1 | SFC regulatory requirement; progressive lifecycle (received→retrieved→generated→completed) | ✓ Good |
| Telegram as primary interface | Advisers want quick mobile access; inline keyboard for draft review is right UX | ✓ Good |
| React web UI as audit/admin only | Separation of concerns; compliance officers get dedicated tool | ✓ Good |
| docling for document parsing | Single library covers PDF/Word/Excel; structured markdown output ideal for RAG | ✓ Good |
| DeepSeek V4 for generation | Strong instruction-following; compliance system prompt effective | ✓ Good |
| Voyage AI for embeddings | Better retrieval quality for financial docs than text-embedding-3-small | ✓ Good |
| cohere rerank-v3.5 | Cross-encoder reranking improves precision before generation | ✓ Good |
| Vision-based PDF parser (pymupdf + qwen3-vl) | Added as spike for complex PDFs; integrated into ingestion pipeline | ✓ Good |
| require_role() factory pattern | Reusable RBAC dependency across all endpoints | ✓ Good |
| Progressive audit lifecycle | status enum transitions (received→retrieved→generated→completed) enable partial trace recovery | ✓ Good |

---
*Last updated: 2026-05-11 after v1.0 milestone*
