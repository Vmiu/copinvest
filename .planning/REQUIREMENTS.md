# Requirements: CopInvest

**Defined:** 2026-05-11
**Core Value:** Advisers can ask a question and get an accurate, source-attributed answer drawn only from approved internal documents — with every interaction fully auditable.

## v2.0 Requirements

### Role Model

- [ ] **ROLE-01**: Admin can access all endpoints previously restricted to `compliance` role (audit log, document registry, ingestion UI)

### Agent Framework

- [ ] **AGENT-01**: LangGraph `StateGraph` orchestrates the pipeline; existing services (query, generation, rerank) become tool nodes with minimal rewrite

### MCP Tool Registry

- [ ] **MCP-01**: Agent can invoke RAG query as an internal tool (query → retrieve → rerank → generate)
- [ ] **MCP-02**: Agent can invoke meeting brief generation as an internal tool
- [ ] **MCP-03**: Agent can invoke follow-up note drafting as an internal tool

### Skills System

- [ ] **SKILL-01**: Skills folder contains Markdown files each with a `description:` frontmatter field and step-by-step tool orchestration instructions
- [ ] **SKILL-02**: On each query, agent reads all skill descriptions and calls fast LLM to select the matching skill; selected skill's full content is injected as system prompt
- [ ] **SKILL-03**: If intent classification fails or is ambiguous, agent falls back to `qa` skill

### Meeting Brief Pipeline

- [ ] **BRIEF-01**: Adviser can request a meeting brief; agent retrieves relevant client/product chunks and generates a structured .docx file
- [ ] **BRIEF-02**: Telegram delivers the .docx and presents Approve/Edit/Discard inline keyboard; adviser action is recorded in audit log

### Follow-Up Note Pipeline

- [ ] **FOLLOW-01**: Adviser can request a follow-up note draft; agent retrieves relevant chunks and generates a compliant .docx file
- [ ] **FOLLOW-02**: Telegram delivers the .docx and presents Approve/Edit/Discard inline keyboard; adviser action is recorded in audit log

### Telegram Scoping

- [ ] **TELE-01**: Q&A and summarize responses are returned inline in Telegram with no Approve/Edit/Discard prompt; adviser action flow is only triggered for BRIEF and FOLLOW pipelines

### Prompt Versioning

- [ ] **PROM-01**: Each prompt template (system prompt + injected skill content) carries a version identifier; version is incremented when the template content changes
- [ ] **PROM-02**: Each audit log entry records `prompt_version` and `skill_version` used; web UI trace inspector displays both fields

### Chunk Metadata Enrichment

- [ ] **META-01**: Every ingested chunk stores the following additional metadata fields in Qdrant payload:
  - `page_number` (int) — page in source document
  - `section_heading` (str) — nearest heading above the chunk
  - `is_table` (bool) — chunk originates from a table
  - `is_figure` (bool) — chunk originates from a figure/image
  - `document_type` (str) — one of: factsheet, compliance_doc, meeting_template, research_report, other
  - `language` (str) — primary language code, e.g. `en`, `zh`
  - `jurisdiction` (str) — e.g. `HK`, `SG`, `global`
  - `product_codes` (list[str]) — product/fund codes mentioned in chunk
  - `chunk_position` (str) — one of: first, middle, last
  - `total_chunks_in_doc` (int) — total chunk count for the parent document
  - `parent_doc_title` (str) — display title of the source document

### Audit Hardening

- [ ] **AUDIT-V2-01**: Audit records are append-only; no UPDATE or DELETE permitted on completed records
- [ ] **AUDIT-V2-02**: When adviser edits a draft, audit log stores both the AI-generated text and the final adviser-edited text; diff is computable from these two fields
- [ ] **AUDIT-V2-03**: Audit records carry a `retention_until` timestamp set to 7 years from creation; admin UI displays retention date per record

## v3 Requirements (deferred)

### Compliance Guardrails

- **COMP-01**: System detects when generated response contains specific investment advice or price targets and flags for review
- **COMP-02**: Faithfulness scoring verifies each claim in the response traces to a retrieved chunk

### Session-Aware Intent Routing

- **SESS-01**: Agent tracks intent history within a session so follow-up messages can inherit prior context (e.g. "now write the follow-up for that")

## Out of Scope

| Feature | Reason |
|---------|--------|
| External MCP server | Internal tool registry only; no external MCP transport/auth needed for v2 |
| Session-aware skill routing | Per-message classification sufficient for v2; deferred to v3 |
| Compliance guardrail layer | Deferred to v3 |
| Faithfulness scoring | Deferred to v3 |
| Multi-tenant SaaS | Single-firm architecture |
| CRM write-back | Read-only for now |
| Autonomous advice delivery | SFC requires human review |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROLE-01 | — | Pending |
| AGENT-01 | — | Pending |
| MCP-01 | — | Pending |
| MCP-02 | — | Pending |
| MCP-03 | — | Pending |
| SKILL-01 | — | Pending |
| SKILL-02 | — | Pending |
| SKILL-03 | — | Pending |
| BRIEF-01 | — | Pending |
| BRIEF-02 | — | Pending |
| FOLLOW-01 | — | Pending |
| FOLLOW-02 | — | Pending |
| TELE-01 | — | Pending |
| PROM-01 | — | Pending |
| PROM-02 | — | Pending |
| META-01 | — | Pending |
| AUDIT-V2-01 | — | Pending |
| AUDIT-V2-02 | — | Pending |
| AUDIT-V2-03 | — | Pending |

**Coverage:**
- v2.0 requirements: 19 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 19 ⚠️

---
*Requirements defined: 2026-05-11*
*Last updated: 2026-05-11 after initial definition*
