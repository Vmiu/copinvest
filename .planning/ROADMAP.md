# Roadmap: CopInvest

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-10)
- ✅ **v2.0 Agent Skills & Audit Hardening** — Phases 6–7 (shipped 2026-05-13)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–5) — SHIPPED 2026-05-10</summary>

- [x] **Phase 1: Data Foundation** — Auth, RBAC, audit schema, Qdrant infrastructure (4/4 plans) — completed 2026-04-29
- [x] **Phase 2: Document Ingestion** — Parse PDF/Word/Excel, chunk, embed into Qdrant (4/4 plans) — completed 2026-05-06
- [x] **Phase 3: RAG Query Pipeline** — Filtered retrieval, reranking, generation, audit logging (3/3 plans) — completed 2026-05-07
- [x] **Phase 4: Telegram Bot** — Primary adviser interface: Q&A, draft review, action tracking (3/3 plans) — completed 2026-05-09
- [x] **Phase 5: Web Audit & Admin UI** — Audit log viewer, trace inspector, document registry, admin ingestion (3/3 plans) — completed 2026-05-10

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v2.0 Agent Skills & Audit Hardening (Phases 6–7) — SHIPPED 2026-05-13</summary>

- [x] **Phase 6: Role Consolidation** — Rename `compliance` → `admin` across DB, enums, RBAC guards, and frontend (3/3 plans) — completed 2026-05-11
- [x] **Phase 7: Chunk Metadata Enrichment** — Add 11 metadata fields to Qdrant payload schema, DB registry, and re-ingest all documents (4/4 plans) — completed 2026-05-11

</details>

### 📋 v3.0 Agent Workflows & Drafting Pipelines

- [ ] **Phase 8: Agent Framework + RAG Tool + Audit Schema** — Prompt-driven agent loop with search_rag tool, freetext intent routing, clarifying questions, and audit schema extension
- [ ] **Phase 9: Client Lookup + Docx Drafting** — search_client tool, meeting brief + follow-up note .docx builders, file storage, and draft_docx agent tool
- [ ] **Phase 10: Audit Dashboard — Tool Call Visibility** — Expandable tool-call trace rows in React audit dashboard, full end-to-end audit visibility
- [ ] **Phase 11: Telegram Integration** — Route all Telegram messages through agent, deliver .docx as Telegram files, link Telegram identity to advisor_id

## Phase Details

### Phase 6: Role Consolidation
**Goal**: The `admin` role replaces `compliance` everywhere — no user-facing surface still references the old name
**Depends on**: Nothing (first v2.0 phase; purely cross-cutting rename)
**Requirements**: ROLE-01
**Success Criteria** (what must be TRUE):
  1. Admin user can log in and access all audit, document registry, and ingestion endpoints that previously required `compliance` role
  2. No endpoint, enum value, DB row, or frontend label contains the string `compliance` in a role context
  3. Existing adviser and senior_adviser tokens continue to work without re-issue
**Plans**: 3 plans
Plans:
- [x] 06-01-PLAN.md — DB migration + Python enum & backend call sites
- [x] 06-02-PLAN.md — Qdrant migration script, seed data, frontend constants
- [x] 06-03-PLAN.md — Test suite updates

### Phase 7: Chunk Metadata Enrichment
**Goal**: Every chunk in Qdrant carries the 11 enriched metadata fields; the document registry reflects the new schema
**Depends on**: Phase 6
**Requirements**: META-01
**Success Criteria** (what must be TRUE):
  1. After re-ingestion, a chunk retrieved via the query API includes `page_number`, `section_heading`, `document_type`, `language`, `jurisdiction`, `product_codes`, `is_table`, `is_figure`, `chunk_position`, `total_chunks_in_doc`, and `parent_doc_title` in its metadata
  2. Admin can filter the document registry by `document_type` and `jurisdiction` using the new fields
  3. Re-ingestion is idempotent — running it twice produces the same Qdrant payload with no duplicate chunks
**Plans**: 4 plans
**Status**: Complete — 2026-05-11
Plans:
- [x] 07-01-PLAN.md — DB migration + chunking service metadata extraction
- [x] 07-02-PLAN.md — Ingestion service + vector repo wiring
- [x] 07-03-PLAN.md — Frontend: extend ingest form + document registry
- [x] 07-04-PLAN.md — Tests

### Phase 8: Agent Framework + RAG Tool + Audit Schema
**Goal**: Advisers send freetext queries and the agent routes them to QA or chat mode, searching documents and citing sources — with tool-call audit infrastructure ready
**Depends on**: Phase 7 (v2.0 complete)
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-05, AGENT-06, AGENT-07, AUDIT-01
**Success Criteria** (what must be TRUE):
  1. Adviser sends a product or regulation question — agent calls `search_rag` and returns a source-attributed answer with `[N]` citations preserved
  2. Adviser sends casual conversation ("hello", "what can you do?") — agent responds without calling any tools (chat mode)
  3. When an adviser's query is ambiguous, the agent asks a clarifying question conversationally before searching
  4. When asked "what documents did you search?", the agent transparently reports what was searched, what was found, and what was not found
  5. The AuditLog table has a `tool_calls` JSON column and every `search_rag` invocation is logged with tool name, input parameters, output summary, and timestamp
**Plans**: TBD
**UI hint**: yes

### Phase 9: Client Lookup + Docx Drafting
**Goal**: Advisers can look up client profiles and the agent generates meeting brief and follow-up note .docx files with proper headers, DRAFT disclaimers, and audit trail
**Depends on**: Phase 8
**Requirements**: AGENT-04, CLIENT-01, CLIENT-02, CLIENT-03, DOCX-01, DOCX-02, DOCX-03, DOCX-04, DOCX-05
**Success Criteria** (what must be TRUE):
  1. Adviser asks "prepare a meeting brief for [client name]" — agent searches client data, asks for date/purpose if missing, generates a .docx with "CopInvest | Meeting Brief | {client}" header and DRAFT disclaimer footer
  2. Adviser asks for a follow-up note — agent generates a .docx with "CopInvest | Follow-Up Note | {client}" header and a distinct disclaimer footer
  3. Generated .docx is saved to `/data/drafts/` with a unique filename and the file path is logged in the audit trail
  4. .docx generation runs in `asyncio.to_thread()` and does not block other concurrent requests
  5. When a client name is not found, the agent receives a clear "client not found" message from `search_client` and relays it to the adviser
**Plans**: TBD
**UI hint**: yes

### Phase 10: Audit Dashboard — Tool Call Visibility
**Goal**: Compliance users can inspect the complete tool-call trace for every query in the React audit dashboard, seeing the sequence of agent decisions from intent through document drafts
**Depends on**: Phase 9 (needs tool calls flowing through the agent pipeline)
**Requirements**: AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. Compliance user opens an audit log entry in the React dashboard and sees expandable rows for each tool call made during that query
  2. Each expandable tool-call row shows the tool name, input parameters (sanitized), output summary, and timestamp in a readable format
  3. Full end-to-end audit trail is visible in the dashboard: user message → agent intent → tool calls in execution order → final response → document file paths
**Plans**: TBD
**UI hint**: yes

### Phase 11: Telegram Integration
**Goal**: Advisers use CopInvest entirely through Telegram — all messages route through the agent, .docx files arrive as downloads, and adviser identity links to client data
**Depends on**: Phase 10
**Requirements**: TELE-01, TELE-02, TELE-03
**Success Criteria** (what must be TRUE):
  1. Adviser sends any message in Telegram — it is routed through the agent orchestration layer, not directly to the QA pipeline
  2. Agent generates a .docx draft — the file is delivered to the adviser via Telegram as a downloadable document with inline keyboard actions
  3. Telegram user identity is linked to `advisor_id` — client lookups return only that adviser's clients
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-29 |
| 2. Document Ingestion | v1.0 | 4/4 | ✓ Complete | 2026-05-06 |
| 3. RAG Query Pipeline | v1.0 | 3/3 | ✓ Complete | 2026-05-07 |
| 4. Telegram Bot | v1.0 | 3/3 | ✓ Complete | 2026-05-09 |
| 5. Web Audit & Admin UI | v1.0 | 3/3 | ✓ Complete | 2026-05-10 |
| 6. Role Consolidation | v2.0 | 3/3 | ✓ Complete | 2026-05-11 |
| 7. Chunk Metadata Enrichment | v2.0 | 4/4 | ✓ Complete | 2026-05-11 |
| 8. Agent Framework + RAG + Audit Schema | v3.0 | 0/TBD | Not started | — |
| 9. Client Lookup + Docx Drafting | v3.0 | 0/TBD | Not started | — |
| 10. Audit Dashboard — Tool Call Visibility | v3.0 | 0/TBD | Not started | — |
| 11. Telegram Integration | v3.0 | 0/TBD | Not started | — |

## Coverage Map (v3.0)

| Requirement | Phase |
|-------------|-------|
| AGENT-01 | Phase 8 |
| AGENT-02 | Phase 8 |
| AGENT-03 | Phase 8 |
| AGENT-05 | Phase 8 |
| AGENT-06 | Phase 8 |
| AGENT-07 | Phase 8 |
| AUDIT-01 | Phase 8 |
| AGENT-04 | Phase 9 |
| CLIENT-01 | Phase 9 |
| CLIENT-02 | Phase 9 |
| CLIENT-03 | Phase 9 |
| DOCX-01 | Phase 9 |
| DOCX-02 | Phase 9 |
| DOCX-03 | Phase 9 |
| DOCX-04 | Phase 9 |
| DOCX-05 | Phase 9 |
| AUDIT-02 | Phase 10 |
| AUDIT-03 | Phase 10 |
| TELE-01 | Phase 11 |
| TELE-02 | Phase 11 |
| TELE-03 | Phase 11 |

**Mapped: 21/21 ✓**

---

*v3.0 roadmap created: 2026-05-13*
