# Requirements: CopInvest

**Defined:** 2026-05-13
**Core Value:** Advisers can ask a question and get an accurate, source-attributed answer drawn only from approved internal documents — with every interaction fully auditable.

## v3 Requirements

Requirements for v3.0 Agent Workflows & Drafting Pipelines. Each maps to roadmap phases.

### Agent Orchestration

- [ ] **AGENT-01**: Prompt-driven agent accepts freetext messages and routes to the appropriate workflow (QA / meeting brief / follow-up note / chat) without explicit mode switching
- [ ] **AGENT-02**: Agent executes a tool-calling loop: call LLM with tools → execute tool calls → return results → loop until final answer, with a hard maximum of 5 tool calls per user message
- [ ] **AGENT-03**: search_rag tool wraps the existing RAG query pipeline (query rewrite → embed → retrieve → rerank → generate) and returns source-attributed results with [N] citations
- [ ] **AGENT-04**: draft_docx tool accepts structured content and document type (brief/follow-up), calls the appropriate builder, saves to /draft/, and returns the file path
- [ ] **AGENT-05**: Agent asks clarifying questions conversationally when required information is missing (client name, meeting date, meeting purpose), maintaining friendly natural dialogue tone
- [ ] **AGENT-06**: Agent is transparent about RAG results — explicitly reports what documents were searched, what was found, and what was not found
- [ ] **AGENT-07**: System prompt includes explicit step sequences for each workflow (meeting brief: identify intent → ask client name → ask date → ask purpose → search RAG → draft docx; QA: search RAG → cite sources; follow-up: similar to brief with different output; chat: conversational response only)

### Client Data

- [ ] **CLIENT-01**: search_client tool retrieves client profile data by advisor_id + client name partial match from a mock JSON data store
- [ ] **CLIENT-02**: ClientDataStore abstract interface (Protocol/ABC) designed for future SQL backend swap — mock JSON implementation behind the interface, not hardcoded in agent
- [ ] **CLIENT-03**: Client not found returns a clear "client not found" message to the agent for relay to the adviser

### Docx Drafting Pipelines

- [ ] **DOCX-01**: build_brief_docx() produces a meeting brief .docx with header ("CopInvest | Meeting Brief | {client}") and footer (DRAFT disclaimer)
- [ ] **DOCX-02**: build_followup_docx() produces a follow-up note .docx with header ("CopInvest | Follow-Up Note | {client}") and footer (different from brief disclaimer)
- [ ] **DOCX-03**: Generated .docx files are saved to /draft/ directory with unique filename; file path is logged in the audit trail
- [ ] **DOCX-04**: .docx generation runs in asyncio.to_thread() to avoid blocking the async event loop
- [ ] **DOCX-05**: Agent presents the generated .docx as a downloadable file with a brief inline summary of contents

### Audit Extensions

- [ ] **AUDIT-01**: Each tool call (search_rag, search_client, draft_docx) is logged with tool name, input parameters, output summary, and timestamp in a tool_calls JSON column on the AuditLog record
- [ ] **AUDIT-02**: Tool call trace is displayed as expandable rows in the React audit log dashboard, showing the sequence of tool invocations within each query
- [ ] **AUDIT-03**: Full end-to-end audit coverage: user message → agent intent → tool calls → final response → document paths, visible in React dashboard

### Telegram Integration

- [ ] **TELE-01**: Telegram message handler routes all incoming messages through the agent orchestration layer instead of directly to the QA pipeline
- [ ] **TELE-02**: Agent .docx drafts are sent via Telegram as downloadable files using send_document() with proper async file handling
- [ ] **TELE-03**: Telegram user identity is linked to advisor_id for client data lookup and audit logging

## Future Requirements

Deferred to a later milestone. Tracked but not in the v3.0 roadmap.

### Audit Hardening (v4.0)

- **AUDIT-V4-01**: Prompt versioning — prompt_version column on AuditLog, templates versioned in /backend/prompts/
- **AUDIT-V4-02**: Adviser edit tracking — diff between AI draft and final adviser-sent version
- **AUDIT-V4-03**: Immutable append-only audit records with 7-year retention enforcement
- **AUDIT-V4-04**: Compliance guardrail layer — faithfulness scoring for generated advice

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| LangGraph / agent framework | v2.0 attempt was "messy/unsatisfying"; replaced by prompt-driven tool calling in v3.0 |
| Internal MCP tool registry | v2.0 MCP approach added unnecessary transport/auth complexity for single-process system |
| Skills system with per-message classification | v2.0 skill-loading approach failed; replaced by prompt-injected workflow guides |
| Session-aware intent routing | Multi-turn session handling deferred to v4.0 |
| Multi-LLM routing (Flash for simple, Pro for complex) | Adds complexity without proportional value at prototype scale |
| Real-time CRM integration | Adds external dependency; mock JSON sufficient for v3.0 |
| Auto-sending drafts to clients | Violates SFC human review requirement |
| Open-ended internet search | Destroys compliance boundary between approved + unapproved content |
| Streaming .docx generation | .docx is not streamable — assembled atomically |
| Agent memory across sessions | Per-message independence; session persistence deferred to v4.0 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| | | |

**Coverage:**
- v3 requirements: [X] total
- Mapped to phases: [Y]
- Unmapped: [Z] ⚠️

---
*Requirements defined: 2026-05-13*
*Last updated: 2026-05-13 after v3.0 requirements definition*
