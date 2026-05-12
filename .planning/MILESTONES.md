# Milestones: CopInvest

## v1.0 MVP

**Shipped:** 2026-05-10
**Phases:** 1–5 | **Plans:** 17 | **Timeline:** 2026-04-29 → 2026-05-10 (12 days)
**Commits:** 145 | **Files changed:** 203 | **Lines added:** ~35,800

### What Shipped

1. JWT auth + role-based access control with Qdrant pre-filtering enforcing sensitivity tiers at the DB layer
2. Full document ingestion pipeline: docling parsing (PDF/Word/Excel) → LLM semantic chunking → embeddings → Qdrant with RBAC metadata
3. RAG query pipeline: query rewrite → Voyage AI embeddings → Qdrant RBAC retrieval → cohere reranking → DeepSeek generation with inline citations
4. Telegram bot as primary adviser interface: Q&A with source citations, Approve/Edit/Discard inline keyboard, full audit write-back
5. React web dashboard: audit log browser, full trace inspector, document registry, admin ingestion UI

### Known Gaps at Close

6 requirements (RAG-01–05, TELE-01) were marked "Pending" in the traceability table — functionality is implemented and verified; documentation gap only.

### Archives

- `.planning/milestones/v1.0-ROADMAP.md`
- `.planning/milestones/v1.0-REQUIREMENTS.md`

## v2.0 Agent Skills & Audit Hardening

**Shipped:** 2026-05-13
**Phases:** 6–7 | **Plans:** 7 | **Timeline:** 2026-05-11 → 2026-05-13 (2 days)

### What Shipped

1. Role consolidation: `compliance` → `admin` rename across DB migrations, enums, RBAC guards, Qdrant, and frontend
2. Chunk metadata enrichment: 11 META-01 fields in Qdrant payload (page_number, section_heading, document_type, language, jurisdiction, product_codes, is_table, is_figure, chunk_position, total_chunks_in_doc, parent_doc_title)
3. DB registry extended with 5 new columns, frontend ingest form + document registry with filters wiring

### Closed Early — Deferred to Next Milestone

Phases 8–10 (Agent Framework, Drafting Pipelines, Audit Hardening) were deferred. The bot needs a workflow redesign to handle 4 distinct modes (brief draft, Q&A, follow-up note, chat) rather than the originally planned LangGraph + skill-classification approach.

### Archives

- `.planning/phases/06-role-consolidation/`
- `.planning/phases/07-chunk-metadata-enrichment/`
