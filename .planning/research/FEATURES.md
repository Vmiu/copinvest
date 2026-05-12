# Feature Research: Prompt-Driven Agent + .docx Drafting + Client Data Retrieval

**Domain:** GenAI assistant for Hong Kong investment advisers (RAG + drafting)
**Researched:** 2026-05-13
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features that, if missing, make the product feel incomplete or broken. Non-negotiable for the v3.0 milestone.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Freetext intent routing (4-mode) | Advisers type naturally — "prepare a brief for Alex Chan next Tuesday" vs "what's the Fidelity fund expense ratio?" Must work without mode buttons. | MEDIUM | `process_query`, `generation_service` | Done via tools array + agent system prompt. LLM decides which tools to call based on user intent. No separate classifier service needed. |
| Tool execution loop (search_rag) | Without this, the agent can't answer product/fund questions. Core RAG pipeline already exists — must be exposed as a tool. | LOW | `query_service.process_query` (exists) | Wrap existing pipeline as `search_rag(query)` tool. Returns text + sources. Separate from the agent's generation step — the agent uses search_rag results as context for its own final answer. |
| Tool execution loop (search_client) | Without this, the agent can't personalize responses. Meeting briefs require client profile data. | MEDIUM | Client JSON files | Mock implementation reading from `demo_material/*.json` + `demo_material/*.md`. Search by `advisor_id` + `client_name` partial match. Returns structured client profile dict. |
| Tool execution loop (draft_docx) | Meeting briefs and follow-up notes must be produced as .docx files, not inline text. Deferred from v2.0. | MEDIUM | `docx_builder.py` (exists, needs upgrade) | Existing `build_brief_docx()` builds flat text. Must be extended with a `build_followup_docx()` variant with different header/footer. |
| .docx with distinct headers/footers | Brief header = "CopInvest \| Meeting Brief \| {client}" with DRAFT disclaimer footer. Follow-up header = "CopInvest \| Follow-Up Note \| {client}" with different footer. | LOW | `python-docx` (already in use) | Use `section.header.paragraphs[0].text` and `section.footer.paragraphs[0].text` as already done in existing `docx_builder.py`. Two template functions: one for each doc type. |
| .docx saved to /draft/ directory | Drafts must be persistent for audit and adviser review. File path must be logged. | LOW | Filesystem (local VM) | `Path("./data/drafts/")` directory already used in `docx_builder.py`. Must log full path in `AuditLog` table (new column or in `llm_response` field). |
| .docx sent via Telegram as file | Primary adviser interface. Draft must be deliverable where the conversation happens. | LOW | `python-telegram-bot` `send_document()` | Use `context.bot.send_document(chat_id=..., document=open(path, 'rb'))` after file is written. |
| All tool calls logged in audit trail | SFC audit requirement. Must show: search_rag called with X, returned Y chunks; search_client called with Z, returned profile; draft_docx called, saved to path P. | MEDIUM | `AuditLog` model, `audit_service` | Extend `AuditLog` table with `tool_calls` JSON column (array of {tool_name, input, output_summary, timestamp}). Or create a separate `ToolCallLog` table. Must be visible in React audit dashboard. |
| Source attribution maintained | All factual claims must cite document source with [N] markers. Non-negotiable for compliance. | LOW | `generation_service._extract_sources()` (exists) | Agent's final answer must include citations. System prompt enforces: "cite sources using [N] from search_rag results." |
| Clarifying questions for ambiguity | Agent must ask "Which client?" when name is ambiguous or missing. Must ask "What date?" when meeting date unspecified for brief/follow-up. | MEDIUM | System prompt design | System prompt instructs: "If the user's intent is unclear, ask ONE clarifying question. Do not guess." Two-turn resolution max before fallback to QA mode. |

### Differentiators (Competitive Advantage)

Features that set CopInvest apart from generic AI assistants. Not expected by users, but highly valued once discovered.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Single freetext interface (no mode buttons) | Eliminates cognitive load of choosing "QA" vs "Brief" vs "Follow-up" vs "Chat." Adviser types naturally; agent figures out intent. This is the #1 UX differentiator. | MEDIUM | Tool definitions, agent prompt | DeepSeek V4 Pro has strong tool-calling capabilities (80.6% SWE-Bench Verified for agentic tasks). The combo of `search_rag`, `search_client`, and `draft_docx` tools with a well-designed system prompt > any mode classifier. |
| Distinct .docx templates (brief vs follow-up) | Professional .docx with correct header/footer per document type shows the product was built by someone who understands adviser workflows. Competitors produce plain markdown. | LOW | `docx_builder.py` | Two builder functions: `build_brief_docx()` and `build_followup_docx()`. Different headers, same core content formatting. Brief header includes meeting date if available. |
| Full tool-call audit trace (not just final output) | Regulators can see not just what was generated, but HOW: which documents were searched, which client was looked up, which tool produced the draft. This exceeds typical "query + response" audit. | MEDIUM | `AuditLog` extension | Each agent turn logs: `{turn_number, tool_name, tool_input, tool_output_summary, timestamp}`. Visible as expandable rows in React audit dashboard. |
| Adviser edit tracking (diff between draft and final) | Shows SFC that human review modified AI output appropriately. Critical for demonstrating "human-in-the-loop" compliance. | MEDIUM | `AuditLog.adviser_edited`, `AdviserAction` (exist, unused) | After adviser approves/edits draft, store final text. Compute simple line-level diff OR store both versions. Existing `update_adviser_action()` handles this — just needs activation in the approve flow. |
| Prompt versioning in audit log | Demonstrates which system prompt template was active when advice was generated. Critical for post-hoc review: "Was this before or after the prompt update?" | LOW | `AuditLog` column, prompt template files | Add `prompt_version` column (string, e.g. "v3.0.0"). Read from template file at agent instantiation. Each deployed prompt gets a version tag. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing but introduce complexity or risk without proportional value.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Explicit mode buttons (QA / Brief / Follow-up / Chat) | Feels safer — eliminates intent detection ambiguity. UX designers love explicit modes. | Forces advisers to think about "which mode" before typing. Adds cognitive load. Creates edge cases when query crosses modes. Same criticism that killed v2.0 skill-classification approach. | Freetext with clarifying questions. If agent is unsure, it asks "Did you want a meeting brief or just product info?" — two-turn resolution is better UX than mode buttons. |
| LangGraph or heavy agent framework | Provides structured state management, built-in tool routing, checkpointing. V2.0 tried this. | V2.0 LangGraph StateGraph wrapping services as tool nodes was "messy/unsatisfying" (per PROJECT.md). Adds dependency, abstraction, debugging complexity. For 4 tools and a single user turn, it's overengineered. | Pure prompt-driven tool calling via DeepSeek's OpenAI-compatible function calling API. Simple while-loop: call LLM with tools + messages, if tool_calls, execute them, append results, loop. Max 5 tool calls per turn to prevent loops. |
| Real-time CRM integration | Eliminates manual client data maintenance. Data always fresh. | Adds external dependency, API auth, error handling, rate limiting, data mapping. Mock JSON is sufficient for prototype. Real CRM integration requires formal agreement, data model alignment, and adds months. | Mock JSON for v3.0. Design client service with abstract interface (`ClientDataStore`) so production CRM can be plugged in later without changing agent code. |
| Multi-LLM routing (use Flash for simple QA, Pro for drafting) | Cost optimization. Flash is cheaper for simple queries. | Adds complexity to routing logic. Different models have different tool-calling quality. Flash may fail on tool selection, causing agent loops. Price difference is negligible at prototype scale (single firm, handful of advisers). | Use DeepSeek V4 Pro for all agent turns. Consistent tool-calling quality. At production scale, evaluate Flash as a possible optimization, not a v3.0 requirement. |
| Auto-sending drafts to clients | Eliminates adviser review step. "Full automation." | Violates SFC requirement for human review. Creates compliance liability. CopInvest's value proposition explicitly states "requires adviser review." | Always require adviser review. Telegram sends .docx with inline keyboard: [Approve] [Edit] [Discard]. Only after explicit approve action is the draft considered "final" — and even then, the adviser manually sends to client. |
| Open-ended internet search as tool | Would let agent answer "what's the market outlook for..." without internal docs. | Destroys compliance boundary. Mixing internal (approved) + external (unapproved) content makes it impossible to certify that all advice came from approved sources. Explicitly rejected in PROJECT.md Out of Scope. | search_rag only. If internal docs don't cover a topic, agent responds: "I don't have approved information on that topic." This is the correct compliance behavior — not a failure. |
| Streaming .docx generation | Looks cool. Users see document being built in real-time. | .docx is not streamable — it's a zip of XML files that must be assembled atomically. False expectation. | Show "Generating draft..." status while agent works, then send complete .docx. Fast enough (sub-5s for a 2-page brief) that streaming isn't needed. |
| Agent memory across Telegram sessions | Would let agent remember client context across days. "Continue where we left off." | Session persistence + intent routing across sessions is explicitly deferred (PROJECT.md: "Session-aware intent routing — per-message classification only for v2.0"). Adds state management complexity. | Each message is independent. Agent reads context fresh. If context needed, adviser re-states it. Session history is available via audit log but not injected into agent context. Deferred to v4.0. |

## Feature Dependencies

```
[Agent Tool Execution Loop]
    ├──requires──> [search_rag tool] ──wraps──> [query_service.process_query] (EXISTS)
    ├──requires──> [search_client tool]
    │                   └──reads──> [demo_material/*.json] (EXISTS)
    │                   └──requires──> [ClientDataStore interface] (NEW abstract class)
    └──requires──> [draft_docx tool]
                        └──requires──> [build_brief_docx()] (EXISTS, needs upgrade)
                        └──requires──> [build_followup_docx()] (NEW)
                        └──saves──> [/draft/ directory]
                        └──sends──> [Telegram send_document()]

[Tool-augmented Audit Logging]
    ├──extends──> [AuditLog model] (EXISTS)
    ├──requires──> [tool_calls column or table] (NEW)
    └──visible_in──> [React audit dashboard] (EXISTS, needs new view)

[Adviser Edit Tracking]
    ├──uses──> [update_adviser_action()] (EXISTS, inactive)
    └──requires──> [Telegram inline keyboard approve/edit/discard] (NEW)

[Prompt Versioning]
    ├──adds──> [prompt_version column] (NEW on AuditLog)
    └──reads──> [prompt template files] (NEW: /backend/prompts/)

[.docx Telegram Delivery]
    ├──uses──> [python-telegram-bot send_document()] (EXISTS in library)
    └──requires──> [inline keyboard for approve/edit/discard] (NEW)

[Freetext Intent Routing]
    ├──depends_on──> [Agent system prompt] (NEW)
    ├──depends_on──> [Tool definitions] (NEW)
    └──conflicts_with──> [Explicit mode buttons] (ANTI-FEATURE — DO NOT BUILD)
```

### Dependency Notes

- **draft_docx tool requires both build_brief_docx() and build_followup_docx():** The agent decides doc type based on user intent and calls the appropriate builder internally. The tool interface is unified: `draft_docx(doc_type, client_name, content, meeting_date?)`.
- **search_client tool requires ClientDataStore interface:** Even though v3.0 uses mock JSON, implement as a clean abstraction (`ClientDataStore.search(advisor_id, client_name) -> ClientProfile`) so the agent tool code doesn't change when upgrading to a DB backend.
- **Tool-augmented audit logging is additive to existing audit:** Current `AuditLog` tracks high-level pipeline stages (received→retrieved→generated→completed). Tool-call logging adds granular sub-steps within the agent turn. They coexist — the high-level status still transitions, but each tool call is also recorded.
- **Adviser edit tracking activates existing unused code:** `update_adviser_action()` and `AdviserAction` enum already exist in the codebase. They just need an activation path (Telegram inline keyboard handler calls them).
- **Freetext intent routing depends on prompt quality, not code complexity:** The routing logic lives in the system prompt, not in Python classifiers. This means prompt iteration is the development workflow — not model training or rule engines.

## MVP Definition

### v3.0 Launch (This Milestone)

Minimum viable agent + drafting — what's needed to replace the "tab-switching" workflow.

- [ ] **Freetext intent routing (4 modes)** — Adviser types naturally; system infers QA/brief/follow-up/chat. Implemented via tool definitions + agent system prompt. No mode buttons, no separate classifier.
- [ ] **search_rag tool** — Wraps existing `process_query()` pipeline. The agent calls this when it needs product/fund/compliance information. Returns text + sources + not_found flag.
- [ ] **search_client tool** — Searches mock JSON by advisor_id + client name. Returns structured client profile (risk tolerance, portfolio, goals, KYC). Required for any personalized response.
- [ ] **draft_docx tool (meeting brief + follow-up note)** — Two builder functions with distinct headers/footers. Saves to `/data/drafts/`. Returns file path for logging and Telegram delivery.
- [ ] **.docx delivered via Telegram** — After draft_docx completes, `send_document()` sends the .docx to the adviser with inline keyboard: [Approve] [Edit] [Discard].
- [ ] **Tool-call audit logging** — Every search_rag, search_client, and draft_docx invocation logged with inputs/outputs summary. Visible in React audit dashboard as expandable rows.
- [ ] **Source citations maintained** — Agent's final answers include [N] citations from search_rag results. Enforced by system prompt.
- [ ] **Clarifying questions for ambiguity** — Agent asks when client name or meeting date is missing/unclear. Two-turn max before fallback.
- [ ] **Adviser edit tracking** — When adviser edits draft before approving, diff stored. Existing `update_adviser_action()` activated.
- [ ] **Prompt versioning** — `prompt_version` recorded in each audit log entry from template file version tag.

### Add After v3.0 Validation

- [ ] **Session-aware context** — Agent remembers client context within a Telegram session (not across days). Deferred from v2.0.
- [ ] **Multi-client meeting briefs** — "Prepare briefs for my 3pm and 4pm meetings" → batch draft generation.
- [ ] **Template customization** — Admin can edit brief/follow-up .docx templates via React dashboard.
- [ ] **Client data UI** — Admin can add/edit client profiles via React dashboard instead of manually editing JSON files.
- [ ] **Agent confidence scoring** — Agent self-reports confidence (HIGH/MEDIUM/LOW) based on retrieval quality.

### Future Consideration (v4.0+)

- [ ] **Real CRM integration** — Replace mock JSON with live CRM read. Abstract interface already designed for this.
- [ ] **Multi-adviser collaboration** — Cross-adviser audit visibility.
- [ ] **Proactive meeting preparation** — Agent detects upcoming meetings from calendar and pre-generates briefs.
- [ ] **Compliance guardrail layer** — Automated faithfulness scoring, mandatory disclaimers, toxicity checks.
- [ ] **Multi-language support** — Cantonese/Mandarin queries with English document retrieval.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Why |
|---------|------------|---------------------|----------|-----|
| Freetext intent routing (4 modes) | HIGH | MEDIUM | P1 | Core UX — without this, no agent behavior |
| search_rag tool | HIGH | LOW | P1 | Exists — just needs tool wrapper |
| search_client tool | HIGH | MEDIUM | P1 | Required for any personalized output |
| draft_docx (brief + follow-up) | HIGH | MEDIUM | P1 | Core deliverable for the milestone |
| .docx Telegram delivery + inline keyboard | HIGH | MEDIUM | P1 | Advisers can't use drafts without delivery |
| Tool-call audit logging | MEDIUM | MEDIUM | P1 | SFC compliance; must ship with agent |
| Source citations maintained | HIGH | LOW | P1 | Already works — must not regress |
| Clarifying questions | MEDIUM | LOW | P1 | Prompt design, not code |
| Adviser edit tracking | MEDIUM | LOW | P2 | Existing code — just activate |
| Prompt versioning | LOW | LOW | P2 | Quick add; important for audit integrity |
| Multi-client batch briefs | MEDIUM | HIGH | P3 | Power user feature; validate basics first |
| Session-aware context | MEDIUM | MEDIUM | P3 | Deferred from v2.0; complex state mgmt |
| Template customization UI | LOW | MEDIUM | P3 | Admin tool; not adviser-facing |
| Real CRM integration | HIGH | HIGH | P4 | Requires external dependencies, agreements |

## Competitor Feature Analysis

CopInvest's primary "competitor" is the manual "tab-switching" workflow (CRM + portfolio system + Word + email). Secondary relevance: generic AI assistants used without compliance guardrails.

| Feature | Manual Workflow | Generic AI Assistant | CopInvest v3.0 |
|---------|-----------------|---------------------|-----------------|
| Freetext intent routing | N/A (human decides) | Partial (some guess intent) | Full 4-mode routing via tools |
| Client-aware responses | Yes (adviser knows client) | No (no client data access) | Yes (search_client tool) |
| Source-attributed answers | Yes (mental model) | No (hallucinates) | Yes (search_rag + [N] citations) |
| .docx drafting | Yes (manual in Word) | No (text only) | Yes (brief + follow-up templates) |
| Compliance audit trail | Partial (emails, CRM logs) | No (no audit) | Yes (full tool-call trace) |
| Adviser review gate | N/A (everything manual) | No (no review step) | Yes (approve/edit/discard) |
| Internal-only content | Yes (by definition) | No (open internet) | Yes (search_rag only) |

**Key insight:** CopInvest doesn't compete with generic AI — it competes with the manual workflow. The v3.0 agent aims to reduce a 15-minute manual process (look up client in CRM, find relevant documents, open Word, draft brief, write email) to a 30-second freetext query + review cycle.

## Sources

- DeepSeek API — Function Calling docs: https://api-docs.deepseek.com/guides/function_calling (HIGH confidence — official docs, accessed 2026-05-13)
- DeepSeek API — Tool Calls guide: https://api-docs.deepseek.com/guides/tool_calls (HIGH confidence — official docs)
- DeepSeek API — Chat Completion parameters (tools, tool_choice): https://api-docs.deepseek.com/api/create-chat-completion (HIGH confidence — official docs)
- python-docx — Header/Footer API: https://github.com/python-openxml/python-docx/blob/master/docs/dev/analysis/features/header.rst (HIGH confidence — official dev docs)
- python-docx — User guide (sections, headers, footers): https://github.com/python-openxml/python-docx/blob/master/docs/user/hdrftr.rst (HIGH confidence — official docs)
- DeepSeek V4 Pro agentic benchmarks: https://www.mindstudio.ai/blog/deepseek-v4-open-source-frontier-model-review (MEDIUM confidence — third-party review, corroborated by official HuggingFace model card)
- CopInvest codebase: `backend/services/query_service.py`, `docx_builder.py`, `audit_service.py`, `models/audit_log.py`, `telegram_bot/handlers.py` (HIGH confidence — primary sources)
- CopInvest PROJECT.md: v3.0 milestone scope, Out of Scope decisions, v2.0 failures (HIGH confidence — project authority)

---

*Feature research for: CopInvest v3.0 — Prompt-Driven Agent Workflows & Drafting Pipelines*
*Researched: 2026-05-13*
