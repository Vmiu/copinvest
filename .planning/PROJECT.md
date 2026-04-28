# CopInvest

## What This Is

A GenAI assistant for investment advisers in Hong Kong that uses retrieval-augmented generation (RAG) over approved internal content to prepare meeting briefs, summarize product information, and draft compliant follow-up notes. It replaces the manual "tab-switching across CRM + portfolio system + Word + email" workflow with a single assistant that synthesizes context and generates first drafts for adviser review.

## Core Value

Advisers can ask a question about a client, product, or meeting and get an accurate, source-attributed answer drawn only from approved internal documents — with every interaction fully auditable.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] RAG-powered Q&A over internal documents (PDFs, Word, Excel/CSV)
- [ ] Sensitivity-tiered document access (role-based permissions on retrieval)
- [ ] Full audit trail (every query, retrieved docs, generated output, adviser edits)
- [ ] Meeting brief generation from client context and internal docs
- [ ] Product information summarization
- [ ] Compliant follow-up note drafting
- [ ] React web UI as primary adviser interface
- [ ] Telegram bot as secondary channel for quick queries
- [ ] Source attribution on all generated responses

### Out of Scope

- Multi-tenant SaaS — this is a personal prototype, single-firm architecture
- Real-time portfolio data feeds — using internal static exports for now
- Mobile native app — web + Telegram covers mobile access
- Graph database (Neo4j) — starting vector-first, can add graph layer later
- CRM write-back — read-only integration initially
- Multi-LLM provider support — OpenAI only for v1

## Context

**Regulatory environment:** Hong Kong SFC (Securities and Futures Commission) guidelines govern how investment advice is documented and communicated. The audit trail must support demonstrating that advice was derived from approved materials.

**Current adviser workflow:** Advisers manually review CRM history, check financial plans, analyze portfolios, run compliance checks, build agendas from scratch, and assemble materials — often spending as much time preparing as conducting meetings. Follow-ups are ad-hoc emails and Word templates edited per client.

**Data landscape:** All content is internal — product factsheets (PDF), compliance docs (Word), policy documents, meeting templates, and structured data (Excel/CSV). No third-party API integrations needed for v1.

**Target users:** Personal prototype for a small group of advisers. Architecture should be clean enough to scale later but doesn't need multi-tenancy now.

## Constraints

- **Tech stack**: Python (FastAPI) backend, React frontend, OpenAI for LLM
- **Vector store**: ChromaDB or FAISS for embeddings with metadata-based permission filtering
- **Deployment**: Local or single cloud VM — no container orchestration for v1
- **Document formats**: Must handle PDF, Word (.docx), and Excel/CSV ingestion
- **Compliance**: All generated content must cite source documents; no hallucinated advice
- **Auditability**: Full trace from query → retrieval → generation → adviser action

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vector-first retrieval (not graph DB) | Simpler for prototype; metadata filtering covers permission needs | — Pending |
| OpenAI as LLM provider | Familiar ecosystem, good Python SDK, strong generation quality | — Pending |
| React + FastAPI architecture | Clean separation of concerns; React for rich UI, FastAPI for async Python backend | — Pending |
| Telegram as secondary channel | Advisers want quick mobile access but primary workflow is desktop web | — Pending |
| Sensitivity tiers for RBAC | Document access driven by adviser seniority/role, not licence types | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-29 after initialization*
