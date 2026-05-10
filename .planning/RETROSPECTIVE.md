# Retrospective: CopInvest

## Milestone: v1.0 MVP

**Shipped:** 2026-05-10
**Phases:** 5 | **Plans:** 17 | **Timeline:** 2026-04-29 → 2026-05-10 (12 days)

### What Was Built

1. JWT auth + Qdrant RBAC pre-filtering enforcing sensitivity tiers at the DB layer
2. docling ingestion pipeline (PDF/Word/Excel) → LLM semantic chunking → embeddings → Qdrant
3. RAG query pipeline: DeepSeek query rewrite → Voyage AI embed → Qdrant RBAC → cohere rerank → DeepSeek generation with inline citations
4. Telegram bot: Q&A with source citations, Approve/Edit/Discard inline keyboard, audit write-back
5. React web dashboard: audit log browser, trace inspector, document registry, admin ingestion UI

### What Worked

- **Phase 1 compliance-first approach**: Building auth, RBAC, and audit trail before any feature work meant every subsequent phase had a solid foundation. No retrofitting security.
- **Progressive audit lifecycle**: The `received→retrieved→generated→completed` status enum made partial trace recovery trivial and gave compliance officers a clear view of where queries failed.
- **Qdrant pre-filtering**: Enforcing RBAC at the vector DB layer (not post-retrieval) was the right call — it's impossible to accidentally leak restricted content through a code bug.
- **docling for parsing**: Single library covering PDF/Word/Excel with structured markdown output was exactly right for RAG. No format-specific edge cases to handle.
- **Telegram as primary interface**: The inline keyboard for Approve/Edit/Discard is a natural fit for mobile advisers. Better UX than a web form.

### What Was Inefficient

- **Traceability table not updated during execution**: RAG-01–05 and TELE-01 were implemented and verified but never marked Complete in REQUIREMENTS.md. Required manual correction at milestone close.
- **Stack drift from original plan**: Started with OpenAI-only, ended with DeepSeek + Voyage AI + cohere. Each switch was justified but added context-switching overhead. A spike on the final stack before Phase 3 would have saved time.
- **Vision parser spike mid-milestone**: The `02-vision-parser` plan was added outside the original roadmap. Good outcome but disrupted the clean phase sequence.

### Patterns Established

- `require_role(*roles)` factory pattern for RBAC on all endpoints — reused across ingest, query, audit, documents routers
- `AsyncOpenAI` client injected as parameter in service functions (not via `get_settings()`) — keeps services testable without config coupling
- `asyncio.to_thread()` for CPU-bound docling parsing — never blocks the event loop
- `db.flush()` in service functions, commit at caller — clean transaction boundary control
- Lazy `fitz` import for pymupdf — avoids import-time errors when vision parser is not used

### Key Lessons

- **Update traceability as you go**: Marking requirements complete during plan execution (not at milestone close) avoids the "6 pending but actually done" situation.
- **Spike the full stack before Phase 3**: If the LLM/embedding/reranking stack will evolve, validate the final combination before building the query pipeline around it.
- **Compliance infrastructure first is non-negotiable**: For regulated domains, auth + audit in Phase 1 is the right call even if it feels like overhead. Every subsequent phase benefited from it.

### Cost Observations

- Model mix: Claude Opus 4.7 (orchestration), DeepSeek V4 (generation/rewrite), Voyage AI (embeddings), cohere (reranking)
- Sessions: ~12 days, ~145 commits
- Notable: DeepSeek V4 Flash for query rewriting with graceful fallback to original query on API error was a good resilience pattern

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 5 |
| Plans | 17 |
| Timeline (days) | 12 |
| Commits | 145 |
| Lines added | ~35,800 |
| Avg plans/phase | 3.4 |
