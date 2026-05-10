# CopInvest

## What This Is

A compliance-aware RAG assistant for investment advisers in Hong Kong. Advisers query it via Telegram to get source-attributed answers from approved internal documents (PDFs, Word, Excel), and can request meeting briefs or follow-up note drafts that are produced as .docx files requiring adviser approval. A React web dashboard gives admin users full audit trail visibility and document management. Every interaction is fully auditable from query through retrieval, generation, and adviser action.

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

- [ ] Role consolidation: rename `compliance` → `admin`; three roles only: advisor, senior_advisor, admin (ROLE-01)
- [ ] Internal MCP tool registry wrapping RAG query, brief generation, follow-up drafting (MCP-01, MCP-02, MCP-03)
- [ ] Skills system: Markdown skill files with description field; per-message intent classification loads matching skill as system prompt (SKILL-01, SKILL-02, SKILL-03)
- [ ] Meeting brief generation pipeline producing .docx output with adviser Approve/Edit/Discard in Telegram (BRIEF-01, BRIEF-02)
- [ ] Compliant follow-up note drafting pipeline producing .docx output with adviser Approve/Edit/Discard in Telegram (FOLLOW-01, FOLLOW-02)
- [ ] Telegram adviser action scoped to drafting pipelines only — Q&A and summarize return inline, no action required (TELE-01)
- [ ] Prompt versioning: prompt templates versioned; each audit log entry records prompt_version and skill_version used (PROM-01, PROM-02)
- [ ] Enriched chunk metadata: page number, section heading, table/figure flag, document type, language, jurisdiction, product codes, chunk position, total chunks, parent doc title (META-01)
- [ ] Immutable append-only audit records with 7-year retention (AUDIT-V2-01, AUDIT-V2-03)
- [ ] Adviser edit tracking with diff between AI draft and final sent version (AUDIT-V2-02)

### Out of Scope

- Multi-tenant SaaS — personal prototype, single-firm architecture
- Real-time portfolio data feeds — internal static exports only
- Mobile native app — web + Telegram covers mobile access
- Graph database (Neo4j) — vector-first is sufficient; graph layer deferred
- CRM write-back — read-only for now
- Multi-LLM provider switching — provider mix already evolved (DeepSeek, Voyage AI, cohere)
- Autonomous advice delivery — SFC requires human review; never auto-send AI output to clients
- Open-ended internet search — mixing internal + external content destroys compliance boundary
- External MCP server — tool registry is internal only; not exposed to Claude Desktop or other MCP clients
- Session-aware intent routing — per-message classification only for v2.0; multi-intent session handling deferred
- Compliance guardrail layer (COMP-01) — deferred; faithfulness scoring (COMP-02) deferred

## Context

**Regulatory environment:** Hong Kong SFC guidelines govern how investment advice is documented. The audit trail must demonstrate that advice was derived from approved materials.

**Current state (v1.0 → v2.0):** ~35,800 lines across Python backend and React frontend. Custom RAG pipeline (no LlamaIndex agent) in `query_service.py`: rewrite → embed → retrieve → rerank → generate. DeepSeek V4 Flash for rewriting/classification, DeepSeek V4 Pro for generation, Voyage AI embeddings, cohere rerank-v3.5, Qdrant vector store. Telegram is the primary adviser interface; React web UI is audit/admin only. Role model had `compliance` where `admin` was intended — corrected in v2.0.

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
| compliance → admin rename | `compliance` role was misnamed; admin is the correct concept for dashboard/doc management access | — Pending |
| Internal MCP tool registry | Tools are internal only — not an external MCP server; avoids auth/transport complexity for v2 | — Pending |
| Per-message skill classification | Intent classified fresh per message using skill descriptions; session-aware routing deferred | — Pending |
| Adviser action scoped to drafting only | Q&A/summarize return inline; only brief+followup .docx pipelines trigger Approve/Edit/Discard | — Pending |
| LangGraph as agent framework | StateGraph wraps existing services as tool nodes; best fit for skill routing without full rewrite | — Pending |

## Current Milestone: v2.0 Agent Skills & Audit Hardening

**Goal:** Evolve the RAG pipeline into a skill-guided agent with internal MCP tools, prompt versioning, enriched chunk metadata, corrected role model, and .docx drafting pipelines with scoped adviser actions.

**Target features:**
- Role consolidation (compliance → admin)
- Internal MCP tool registry (RAG, brief, followup)
- Skills system with per-message intent classification
- Meeting brief + follow-up note .docx pipelines
- Telegram adviser action scoped to drafting only
- Prompt + skill versioning in audit log
- Enriched chunk metadata (12 new fields)
- Audit hardening (immutable records, 7-year retention, edit diff)

---
*Last updated: 2026-05-11 after v2.0 milestone start*
