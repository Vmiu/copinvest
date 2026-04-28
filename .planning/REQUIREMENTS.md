# Requirements: CopInvest

**Defined:** 2026-04-29
**Core Value:** Advisers can ask a question and get an accurate, source-attributed answer from approved internal documents — with every interaction fully auditable.

## v1 Requirements

### Document Ingestion

- [ ] **INGEST-01**: System can parse PDF documents and extract text with table structure preserved
- [ ] **INGEST-02**: System can parse Word (.docx) documents and extract text with formatting preserved
- [ ] **INGEST-03**: System can parse Excel/CSV files with column headers preserved per row
- [ ] **INGEST-04**: Admin can assign a sensitivity tier (Public/Internal/Restricted/Confidential) to each document at ingestion
- [ ] **INGEST-05**: Each chunk is tagged with source_id, doc_type, sensitivity_tier, and allowed_roles metadata
- [ ] **INGEST-06**: Documents are chunked using semantic/structural boundaries (section headers, paragraphs) not fixed token counts
- [ ] **INGEST-07**: Financial tables are kept as complete units during chunking, not split across chunks
- [ ] **INGEST-08**: Ingestion logs parsing quality metrics (character count, warnings, extraction method) per document

### RAG Query

- [ ] **RAG-01**: User can ask a natural language question and receive an answer sourced from internal documents
- [ ] **RAG-02**: Every response includes inline source citations with document name and section reference
- [ ] **RAG-03**: System returns "not found in approved documents" when retrieval confidence is below threshold
- [ ] **RAG-04**: Retrieved chunks are reranked by a cross-encoder before being sent to the LLM
- [ ] **RAG-05**: System prompt constrains the LLM to answer only from provided context, never from training data

### Access Control

- [ ] **AUTH-01**: User can log in with email and password and receive a JWT token
- [ ] **AUTH-02**: User session persists across browser refresh via stored JWT
- [ ] **AUTH-03**: Each user has a role (adviser, senior_adviser, compliance) that determines document access
- [ ] **AUTH-04**: Document retrieval is filtered by user role at the vector store query layer (pre-retrieval, not post-retrieval)
- [ ] **AUTH-05**: A junior adviser cannot retrieve or see any content from Restricted or Confidential tier documents

### Audit Trail

- [ ] **AUDIT-01**: Every query produces an audit record with: trace_id, user_id, timestamp, query_text, retrieved_chunks, prompt_sent, llm_response, model_version
- [ ] **AUDIT-02**: Audit records are grouped by session, each session recorded with start/end DateTime
- [ ] **AUDIT-03**: Audit records include the exact pinned model version used for generation
- [ ] **AUDIT-04**: Adviser action (sent/discarded/saved) is recorded in the audit trail
- [ ] **AUDIT-05**: Audit records include which sensitivity tier was accessed per query

### Web UI

- [ ] **UI-01**: User can type a question and see a streaming response rendered in real-time
- [ ] **UI-02**: Each response displays a source attribution panel showing which documents were used
- [ ] **UI-03**: All generated output is labeled as "Draft" and requires explicit adviser review before use
- [ ] **UI-04**: User can mark a response as "sent", "edited", or "discarded" to record their action

### Telegram Bot

- [ ] **TELE-01**: User can send a text message to the Telegram bot and receive a text answer with source citations
- [ ] **TELE-02**: Telegram bot validates webhook secret on every incoming request

## v2 Requirements

### Meeting Briefs

- **BRIEF-01**: User can generate a structured meeting brief from client context and internal docs
- **BRIEF-02**: Meeting brief includes agenda items, relevant product info, and compliance notes

### Follow-Up Notes

- **FOLLOW-01**: User can generate a post-meeting follow-up note draft with action items
- **FOLLOW-02**: Follow-up notes cite source documents for any product or compliance references

### Audit Enhancements

- **AUDIT-V2-01**: Immutable append-only audit records (INSERT-only, no UPDATE or DELETE)
- **AUDIT-V2-02**: Adviser edit tracking with diff between AI draft and final sent version
- **AUDIT-V2-03**: 7-year retention policy with partitioned storage

### Telegram Enhancements

- **TELE-V2-01**: Telegram user mapping to internal accounts (telegram_user_id → internal user_id)
- **TELE-V2-02**: Role-based access control applied to Telegram queries

### Compliance

- **COMP-01**: Compliance guardrail layer (detect specific investment advice, price targets, forward-looking statements)
- **COMP-02**: Faithfulness scoring (verify each claim traces to a retrieved chunk)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time market data / price lookups | Requires licensed data feeds; scope to internal static documents only |
| Specific investment recommendations ("buy X") | Tool assists advisers, doesn't replace them; regulatory boundary |
| CRM write-back | Read-only for v1; write-back adds integration complexity |
| Multi-LLM provider switching | OpenAI sufficient for v1; abstract interface for future swap |
| Meeting transcription / recording | Separate compliance domain (recording consent); out of scope |
| Open-ended internet search | Mixing internal + external content destroys compliance boundary |
| Mobile native app | Web + Telegram covers mobile access |
| Multi-tenant SaaS | Personal prototype; single-firm architecture |
| Autonomous advice delivery | SFC requires human review; never auto-send AI output to clients |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | — | Pending |
| INGEST-02 | — | Pending |
| INGEST-03 | — | Pending |
| INGEST-04 | — | Pending |
| INGEST-05 | — | Pending |
| INGEST-06 | — | Pending |
| INGEST-07 | — | Pending |
| INGEST-08 | — | Pending |
| RAG-01 | — | Pending |
| RAG-02 | — | Pending |
| RAG-03 | — | Pending |
| RAG-04 | — | Pending |
| RAG-05 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| AUTH-05 | — | Pending |
| AUDIT-01 | — | Pending |
| AUDIT-02 | — | Pending |
| AUDIT-03 | — | Pending |
| AUDIT-04 | — | Pending |
| AUDIT-05 | — | Pending |
| UI-01 | — | Pending |
| UI-02 | — | Pending |
| UI-03 | — | Pending |
| UI-04 | — | Pending |
| TELE-01 | — | Pending |
| TELE-02 | — | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 0
- Unmapped: 29 ⚠️

---
*Requirements defined: 2026-04-29*
*Last updated: 2026-04-29 after initial definition*
