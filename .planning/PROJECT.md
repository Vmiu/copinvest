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
- ✓ Role consolidation (compliance → admin) — v2.0
- ✓ Enriched chunk metadata (11 fields in Qdrant payload) — v2.0

### Active

<!-- Current scope. Building toward these. -->

- [ ] Prompt-driven agent: step-by-step workflow guides injected into system prompt; LLM decides tool usage, asks clarifying questions when needed (AGENT-01)
- [ ] Client info retrieval: searchable by advisor_id + client name; mock JSON data for now, designed for future DB backend (CLIENT-01, CLIENT-02)
- [ ] Meeting brief .docx pipeline: header/footer, sent via Telegram, saved to /draft/, file path logged in audit (BRIEF-01, BRIEF-02, BRIEF-03)
- [ ] Follow-up note .docx pipeline: different header/footer, same save/log pattern (FOLLOW-01, FOLLOW-02, FOLLOW-03)
- [ ] 4-mode freetext workflow: QA, meeting brief, follow-up note, chat — no explicit mode switching, intent inferred by LLM (WORKFLOW-01, WORKFLOW-02)
- [ ] Tool-augmented audit logging: search_rag, search_client, draft_docx calls logged; full trace visible in React audit dashboard (AUDIT-V3-01, AUDIT-V3-02)
- [ ] Prompt versioning: templates versioned; each audit log entry records prompt_version used (PROM-01, PROM-02)
- [ ] Immutable append-only audit records with 7-year retention (AUDIT-V2-01)
- [ ] Adviser edit tracking: diff between AI draft and final sent version (AUDIT-V2-02)

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
- Internal MCP tool registry (MCP-01, MCP-02, MCP-03) — v2.0 LangGraph + MCP approach was messy/unsatisfying; replaced by simpler prompt-driven tool calls in v3.0
- Skills system with per-message classification (SKILL-01, SKILL-02, SKILL-03) — v2.0 skill-loading approach failed; replaced by prompt-injected workflow guides in v3.0
- LangGraph agent framework — v2.0 StateGraph wrapping services as tool nodes was unsatisfying; replaced by prompt-driven orchestration in v3.0

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

## Current Milestone: v3.0 Agent Workflows & Drafting Pipelines

**Goal:** Replace the failed LangGraph/skill-classification approach with a simple prompt-driven agent that handles 4 modes (QA, meeting brief, follow-up note, chat) via freetext — extracting client info, searching RAG, and drafting .docx files with headers/footers, all fully audited.

**Target features:**
- Prompt-driven agent with step-by-step workflow guides injected into system prompt
- Client info retrieval by advisor_id + client name (mock JSON backend)
- Meeting brief + follow-up note .docx pipelines with distinct headers/footers
- Telegram delivery, /draft/ storage, file path in audit log
- 4-mode freetext workflow — no explicit mode switching
- Full audit coverage for all tool calls visible in React dashboard

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
*Last updated: 2026-05-13 after v3.0 milestone start*
