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
