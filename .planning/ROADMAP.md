# Roadmap: CopInvest

## Milestones

- ✅ **v1.0 MVP** — Phases 1–5 (shipped 2026-05-10)
- 📋 **v2.0 Agent Skills & Audit Hardening** — Phases 6–10 (planned 2026-05-11)

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

### 📋 v2.0 Agent Skills & Audit Hardening

- [x] **Phase 6: Role Consolidation** — Rename `compliance` → `admin` across DB, enums, RBAC guards, and frontend (3/3 plans) — completed 2026-05-11
- [ ] **Phase 7: Chunk Metadata Enrichment** — Add 11 metadata fields to Qdrant payload schema, DB registry, and re-ingest all documents
- [ ] **Phase 8: Agent Framework & Skills** — LangGraph StateGraph wraps existing services as tool nodes; skills system with per-message intent classification
- [ ] **Phase 9: Drafting Pipelines** — Meeting brief and follow-up note .docx generation with Telegram Approve/Edit/Discard; Q&A scoped to inline-only
- [ ] **Phase 10: Audit Hardening & Prompt Versioning** — Immutable audit records, 7-year retention, edit diff storage, prompt/skill version tracking

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
**Plans**: TBD
**UI hint**: yes

### Phase 8: Agent Framework & Skills
**Goal**: Queries are routed through a LangGraph StateGraph that classifies intent, loads the matching skill as system prompt, and dispatches to the correct internal tool
**Depends on**: Phase 7
**Requirements**: AGENT-01, MCP-01, MCP-02, MCP-03, SKILL-01, SKILL-02, SKILL-03
**Success Criteria** (what must be TRUE):
  1. A Q&A query flows through the LangGraph graph and returns a source-attributed answer — existing retrieval quality is preserved
  2. Sending a query that matches the `brief` skill causes the agent to load the brief skill's system prompt and invoke the brief tool node
  3. An ambiguous or unrecognised query falls back to the `qa` skill without error
  4. Skills folder contains at least `qa`, `brief`, and `followup` Markdown files each with a `description:` frontmatter field
**Plans**: TBD

### Phase 9: Drafting Pipelines
**Goal**: Advisers can request meeting briefs and follow-up notes via Telegram and receive a .docx file with an Approve/Edit/Discard keyboard; Q&A and summarize return inline with no action prompt
**Depends on**: Phase 8
**Requirements**: BRIEF-01, BRIEF-02, FOLLOW-01, FOLLOW-02, TELE-01
**Success Criteria** (what must be TRUE):
  1. Adviser sends a brief request in Telegram and receives a .docx attachment with an Approve/Edit/Discard inline keyboard
  2. Adviser sends a follow-up note request in Telegram and receives a .docx attachment with an Approve/Edit/Discard inline keyboard
  3. Adviser action (Approve/Edit/Discard) on a brief or follow-up is recorded in the audit log
  4. A plain Q&A query in Telegram returns an inline answer with no Approve/Edit/Discard prompt
**Plans**: TBD
**UI hint**: yes

### Phase 10: Audit Hardening & Prompt Versioning
**Goal**: Audit records are immutable and retention-stamped; every record traces the exact prompt and skill version used; admin UI exposes retention dates and version fields
**Depends on**: Phase 9
**Requirements**: PROM-01, PROM-02, AUDIT-V2-01, AUDIT-V2-02, AUDIT-V2-03
**Success Criteria** (what must be TRUE):
  1. Attempting to UPDATE or DELETE a completed audit record via the API returns an error; only INSERT is permitted
  2. When an adviser edits a draft, the audit record stores both the original AI-generated text and the final edited text
  3. Each audit record displays a `retention_until` date (creation + 7 years) in the admin UI trace inspector
  4. The trace inspector shows `prompt_version` and `skill_version` for every audit record
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-29 |
| 2. Document Ingestion | v1.0 | 4/4 | ✓ Complete | 2026-05-06 |
| 3. RAG Query Pipeline | v1.0 | 3/3 | ✓ Complete | 2026-05-07 |
| 4. Telegram Bot | v1.0 | 3/3 | ✓ Complete | 2026-05-09 |
| 5. Web Audit & Admin UI | v1.0 | 3/3 | ✓ Complete | 2026-05-10 |
| 6. Role Consolidation | v2.0 | 3/3 | ✓ Complete | 2026-05-11 |
| 7. Chunk Metadata Enrichment | v2.0 | 0/? | Not started | — |
| 8. Agent Framework & Skills | v2.0 | 0/? | Not started | — |
| 9. Drafting Pipelines | v2.0 | 0/? | Not started | — |
| 10. Audit Hardening & Prompt Versioning | v2.0 | 0/? | Not started | — |

## Coverage Map (v2.0)

| Requirement | Phase |
|-------------|-------|
| ROLE-01 | Phase 6 |
| META-01 | Phase 7 |
| AGENT-01 | Phase 8 |
| MCP-01 | Phase 8 |
| MCP-02 | Phase 8 |
| MCP-03 | Phase 8 |
| SKILL-01 | Phase 8 |
| SKILL-02 | Phase 8 |
| SKILL-03 | Phase 8 |
| BRIEF-01 | Phase 9 |
| BRIEF-02 | Phase 9 |
| FOLLOW-01 | Phase 9 |
| FOLLOW-02 | Phase 9 |
| TELE-01 | Phase 9 |
| PROM-01 | Phase 10 |
| PROM-02 | Phase 10 |
| AUDIT-V2-01 | Phase 10 |
| AUDIT-V2-02 | Phase 10 |
| AUDIT-V2-03 | Phase 10 |

**Mapped: 19/19 ✓**

---
*v2.0 roadmap created: 2026-05-11*
