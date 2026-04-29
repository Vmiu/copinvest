# Roadmap: CopInvest

## Overview

Build a compliance-aware RAG assistant for HK investment advisers in five phases. The foundation establishes auth, RBAC, and audit infrastructure (SFC-mandated from day one). Ingestion and query pipelines follow. Telegram is the primary adviser interface — it delivers the full Q&A and human-review workflow. The React web UI is an audit and admin tool for compliance officers and admins, not a chat interface.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Foundation** - Auth, RBAC, audit schema, and Qdrant/PostgreSQL infrastructure
- [ ] **Phase 2: Document Ingestion** - Parse PDF/Word/Excel, chunk, tag metadata, embed into Qdrant
- [ ] **Phase 3: RAG Query Pipeline** - Filtered retrieval, reranking, generation, audit logging
- [ ] **Phase 4: Telegram Bot** - Primary adviser interface: Q&A with source citations, draft review flow, action tracking
- [ ] **Phase 5: Web Audit & Admin UI** - Audit log viewer, trace inspector, document registry, admin ingestion UI

## Phase Details

### Phase 1: Data Foundation
**Goal**: The security and compliance infrastructure is in place — users can authenticate, roles control document access, and every future query will have an audit record
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05
**Success Criteria** (what must be TRUE):
  1. User can log in with email/password and receive a JWT token that persists across browser refresh
  2. A junior adviser role cannot retrieve content from Restricted or Confidential tier documents (enforced at Qdrant query layer, not post-retrieval)
  3. Every query produces an audit record containing trace_id, user_id, timestamp, query_text, retrieved_chunks, prompt_sent, llm_response, and pinned model version
  4. Audit records are grouped by session with start/end DateTime and record which sensitivity tier was accessed
  5. Adviser action (sent/discarded/saved) is captured in the audit trail
**Plans:** 4 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffold, models, config, database, Docker Compose, test infrastructure
- [ ] 01-02-PLAN.md — Auth system: JWT, password hashing, login endpoint, user seeding
- [ ] 01-03-PLAN.md — Audit trail and session management services with progressive lifecycle
- [ ] 01-04-PLAN.md — Qdrant RBAC: collection setup, pre-retrieval filtering, access control tests

### Phase 2: Document Ingestion
**Goal**: Admins can ingest PDF, Word, and Excel documents with sensitivity tiers assigned, and all content is correctly chunked and embedded in Qdrant with full metadata
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08
**Success Criteria** (what must be TRUE):
  1. Admin can ingest a PDF and the extracted text preserves table structure; a Word doc preserves formatting; an Excel/CSV preserves column headers per row
  2. Admin can assign a sensitivity tier (Public/Internal/Restricted/Confidential) to each document at ingestion time
  3. Each chunk in Qdrant carries source_id, doc_type, sensitivity_tier, and allowed_roles metadata
  4. Financial tables are stored as complete chunks — no table is split across chunk boundaries
  5. Ingestion produces a log entry per document with character count, warnings, and extraction method
**Plans**: TBD

### Phase 3: RAG Query Pipeline
**Goal**: Users can ask natural language questions and receive accurate, source-attributed answers drawn only from approved documents, with every interaction audited
**Depends on**: Phase 2
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04, RAG-05
**Success Criteria** (what must be TRUE):
  1. User can ask a question and receive an answer with inline source citations (document name and section reference)
  2. When no relevant content exists above the confidence threshold, the system returns "not found in approved documents" rather than generating an answer
  3. Retrieved chunks are reranked by a cross-encoder before being passed to the LLM
  4. The system prompt prevents the LLM from answering from training data — all answers trace to retrieved chunks
**Plans**: TBD

### Phase 4: Telegram Bot
**Goal**: Advisers can query the system via Telegram, receive sourced answers, review each draft via inline keyboard, and have every action recorded in the audit trail
**Depends on**: Phase 3
**Requirements**: TELE-01, TELE-02, TELE-03, TELE-04
**Success Criteria** (what must be TRUE):
  1. Adviser can send a text message to the bot and receive a text answer with inline source citations
  2. The bot rejects any incoming request that fails webhook secret validation
  3. Each answer is presented as a draft with an inline keyboard offering Approve / Edit / Discard — the response is not considered final until the adviser acts
  4. The adviser's action (approved/edited/discarded) is recorded in the audit trail against the originating query trace_id
**Plans**: TBD

### Phase 5: Web Audit & Admin UI
**Goal**: Compliance officers and admins can inspect the full audit trail, drill into individual query traces, view the document registry, and trigger ingestion — all from a React dashboard
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. Admin can browse the audit log filtered by session, user, and date range and see every query with its outcome
  2. Admin can open any audit record and view the complete trace: query → retrieved chunks → prompt sent → LLM response → adviser action
  3. Admin can view the document registry listing all ingested documents with sensitivity tier, chunk count, and ingestion date
  4. Admin can trigger document ingestion and assign sensitivity tiers through the UI without using the CLI
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5
(Phase 4 and Phase 5 both depend on Phase 3 and can be worked in sequence or parallel once Phase 3 is complete)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/4 | Planning complete | - |
| 2. Document Ingestion | 0/TBD | Not started | - |
| 3. RAG Query Pipeline | 0/TBD | Not started | - |
| 4. Telegram Bot | 0/TBD | Not started | - |
| 5. Web Audit & Admin UI | 0/TBD | Not started | - |
