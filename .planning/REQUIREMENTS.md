# Requirements: CopInvest

**Defined:** 2026-04-29
**Core Value:** Advisers can ask a question and get an accurate, source-attributed answer from approved internal documents — with every interaction fully auditable.

## v1 Requirements

### Document Ingestion

- [x] **INGEST-01**: System can parse PDF documents and extract text with table structure preserved
- [x] **INGEST-02**: System can parse Word (.docx) documents and extract text with formatting preserved
- [x] **INGEST-03**: System can parse Excel/CSV files with column headers preserved per row
- [x] **INGEST-04**: Admin can assign a sensitivity tier (Public/Internal/Restricted/Confidential) to each document at ingestion
- [x] **INGEST-05**: Each chunk is tagged with source_id, doc_type, sensitivity_tier, and allowed_roles metadata
- [x] **INGEST-06**: Documents are chunked using semantic/structural boundaries (section headers, paragraphs) not fixed token counts
- [x] **INGEST-07**: Financial tables are kept as complete units during chunking, not split across chunks
- [x] **INGEST-08**: Ingestion logs parsing quality metrics (character count, warnings, extraction method) per document

### RAG Query

- [ ] **RAG-01**: User can ask a natural language question and receive an answer sourced from internal documents
- [ ] **RAG-02**: Every response includes inline source citations with document name and section reference
- [ ] **RAG-03**: System returns "not found in approved documents" when retrieval confidence is below threshold
- [ ] **RAG-04**: Retrieved chunks are reranked by a cross-encoder before being sent to the LLM
- [ ] **RAG-05**: System prompt constrains the LLM to answer only from provided context, never from training data

### Access Control

- [x] **AUTH-01**: User can log in with email and password and receive a JWT token
- [x] **AUTH-02**: User session persists across browser refresh via stored JWT
- [x] **AUTH-03**: Each user has a role (adviser, senior_adviser, compliance) that determines document access
- [x] **AUTH-04**: Document retrieval is filtered by user role at the vector store query layer (pre-retrieval, not post-retrieval)
- [x] **AUTH-05**: A junior adviser cannot retrieve or see any content from Restricted or Confidential tier documents

### Audit Trail

- [x] **AUDIT-01**: Every query produces an audit record with: trace_id, user_id, timestamp, query_text, retrieved_chunks, prompt_sent, llm_response, model_version
- [x] **AUDIT-02**: Audit records are grouped by session, each session recorded with start/end DateTime
- [x] **AUDIT-03**: Audit records include the exact pinned model version used for generation
- [x] **AUDIT-04**: Adviser action (sent/discarded/saved) is recorded in the audit trail
- [x] **AUDIT-05**: Audit records include which sensitivity tier was accessed per query

### Telegram Bot (Primary Adviser Interface)

- [ ] **TELE-01**: Adviser can send a text message to the Telegram bot and receive a text answer with inline source citations (document name and section reference)
- [ ] **TELE-02**: Bot authenticates incoming requests using Telegram's bot token mechanism (long-polling mode — no webhook secret required; bot raises ValueError on startup if TELEGRAM_BOT_TOKEN is not set)
- [ ] **TELE-03**: Bot presents each generated answer as a draft with an inline keyboard offering Approve / Edit / Discard actions before the response is considered final
- [ ] **TELE-04**: Adviser action (approved/edited/discarded) selected via inline keyboard is recorded in the audit trail against the originating query

### Web Audit & Admin UI

- [ ] **UI-01**: Admin/compliance user can browse the audit log filtered by session, user, and date range
- [ ] **UI-02**: Admin can open any audit record and view the full trace: query → retrieved chunks → prompt sent → LLM response → adviser action
- [ ] **UI-03**: Admin can view the document registry showing all ingested documents with their sensitivity tier, chunk count, and ingestion date
- [ ] **UI-04**: Admin can trigger document ingestion and assign sensitivity tiers through the UI without using the CLI

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
| AUTH-01 | Phase 1 | Complete (01-02) |
| AUTH-02 | Phase 1 | Complete (01-02) |
| AUTH-03 | Phase 1 | Complete (01-01) |
| AUTH-04 | Phase 1 | Complete (01-04) |
| AUTH-05 | Phase 1 | Complete (01-04) |
| AUDIT-01 | Phase 1 | Complete (01-01) |
| AUDIT-02 | Phase 1 | Complete (01-03) |
| AUDIT-03 | Phase 1 | Complete (01-03) |
| AUDIT-04 | Phase 1 | Complete (01-03) |
| AUDIT-05 | Phase 1 | Complete (01-03) |
| INGEST-01 | Phase 2 | Complete (02-03) |
| INGEST-02 | Phase 2 | Complete (02-03) |
| INGEST-03 | Phase 2 | Complete (02-03) |
| INGEST-04 | Phase 2 | Complete (02-01) |
| INGEST-05 | Phase 2 | Complete (02-01) |
| INGEST-06 | Phase 2 | Complete (02-02) |
| INGEST-07 | Phase 2 | Complete (02-02) |
| INGEST-08 | Phase 2 | Complete (02-01) |
| RAG-01 | Phase 3 | Pending |
| RAG-02 | Phase 3 | Pending |
| RAG-03 | Phase 3 | Pending |
| RAG-04 | Phase 3 | Pending |
| RAG-05 | Phase 3 | Pending |
| TELE-01 | Phase 4 | Pending |
| TELE-02 | Phase 4 | Pending |
| TELE-03 | Phase 4 | Pending |
| TELE-04 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-29*
*Last updated: 2026-04-29 — Telegram expanded to primary interface (TELE-03, TELE-04 added); UI requirements rewritten as audit/admin dashboard*
