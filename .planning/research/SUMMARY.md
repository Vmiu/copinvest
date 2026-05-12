# Project Research Summary

**Project:** CopInvest
**Domain:** GenAI assistant for Hong Kong investment advisers — RAG + agent-driven drafting
**Researched:** 2026-05-13
**Confidence:** MEDIUM-HIGH

## Executive Summary

CopInvest v3.0 introduces prompt-driven agent workflows and .docx drafting to replace the manual "tab-switching across CRM + portfolio system + Word + email" workflow. The core insight: a single freetext interface where advisers type naturally and the agent infers intent (QA, meeting brief, follow-up note, or general chat) by selecting from three tools — `search_rag` (existing RAG pipeline), `search_client` (client profile lookup), and `draft_docx` (document generation). No mode buttons, no separate classifier, no agent framework — pure prompt-driven orchestration using DeepSeek V4 Pro's OpenAI-compatible tool-calling API.

The recommended approach is deliberately minimal. The v2.0 experiment with LangGraph StateGraph was abandoned as "messy/unsatisfying." For a 3-tool single-turn agent, a simple while-loop (send messages to LLM → inspect tool_calls → execute tools → append results → repeat, max 5 turns) is sufficient. All audit logging uses existing SQLAlchemy infrastructure extended with a JSON column for tool-call traces and a string column for prompt versioning. Client data is served from mock JSON files behind an abstract `ClientDataStore` interface, ensuring the tool code doesn't change when upgrading to a real CRM in v4.0.

The critical risk is **source citation breakage**: the existing RAG pipeline returns answers with `[N]` citations, but when the agent paraphrases RAG output in its final answer, those citations can be silently dropped — violating SFC compliance requirements. Mitigation is a three-layer defense: system prompt enforcement ("MUST preserve `[N]` markers"), post-generation automated validation (flag if `search_rag` was called but no `[N]` markers appear in final output), and tool output format design that makes citations hard to strip. Other risks include agent tool-loop runaway (prevented by a hard 5-turn limit and idempotency checks), prompt injection via client data (prevented by context wrapping markers and data sanitization), and .docx header/footer loss on save (prevented by post-save validation).

## Key Findings

### Recommended Stack

The v3.0 milestone requires **no new package installations** — all additions use existing dependencies (`openai`, `python-docx`, `sqlalchemy`, `python-telegram-bot`). The stack approach is: leverage what's already proven, extend where needed, abstract where future change is expected.

**Core technologies:**
- **DeepSeek V4 Pro (tool-calling mode)** — agent LLM for intent routing, tool selection, and final generation. 80.6% SWE-Bench Verified for agentic tasks. Uses existing `AsyncOpenAI` client — no new SDK. Three reasoning modes (non-think/think-high/think-max) for adjustable depth.
- **Prompt-driven orchestration (no framework)** — a 30-line while-loop replaces what LangGraph required 200+ lines to do poorly. Reason: v2.0 LangGraph StateGraph approach was abandoned as "messy/unsatisfying." For 3 tools and a single-turn agent, the LLM's native tool-calling is sufficient.
- **Mock JSON ClientDataStore (abstract interface)** — two demo profiles in `demo_material/` served behind an `abc.ABC` interface. Schema not finalized, CRM integration deferred to v4.0. The abstract interface ensures today's investment isn't wasted when upgrading.
- **python-docx (already installed)** — extended with `build_followup_docx()` alongside existing `build_brief_docx()`. Distinct headers/footers per document type with DRAFT disclaimers.
- **SQLAlchemy JSON column** — stores tool-call trace `[{turn, tool_name, tool_input, tool_output_summary, timestamp}]` directly on the existing `AuditLog` model. Rejected separate `ToolCallLog` table as premature normalization for 3-5 calls/turn.
- **Versioned prompt .txt files** — stored in `backend/prompts/agent_v3_0_0.txt`. Version tag embedded in file header, recorded in `AuditLog.prompt_version`. Prompt iteration = git-tracked file changes, not code deploys.

**Key stack decisions:**
- No LangGraph/LangChain (v2.0 failure proven)
- No separate mode classifier (LLM tool selection replaces it)
- No multi-LLM routing (Flash for simple QA deferred — price difference negligible at prototype scale)
- No real CRM integration (abstract interface designed, deferred to v4.0)

### Expected Features

The v3.0 feature set is laser-focused on replacing the manual "15-minute tab-switching" workflow with a "30-second freetext query + review cycle."

**Must have (table stakes) — all P1 priority:**
- **Freetext intent routing (4 modes)** — adviser types naturally; system infers QA/brief/follow-up/chat. Implemented via tool definitions + system prompt. No mode buttons.
- **search_rag tool** — wraps existing `process_query()` pipeline. Agent calls this for product/fund/compliance information. Returns source-attributed text with `[N]` markers.
- **search_client tool** — searches mock JSON by advisor_id + client name. Returns structured client profile (risk tolerance, portfolio, goals, KYC). Required for any personalized response.
- **draft_docx tool (brief + follow-up)** — two builder functions with distinct headers ("CopInvest | Meeting Brief | {client}" vs "CopInvest | Follow-Up Note | {client}") and different DRAFT disclaimer footers. Saves to `/data/drafts/`.
- **.docx delivered via Telegram** — `send_document()` with inline keyboard: [Approve] [Edit] [Discard]. Advisers primarily use Telegram — no web download path needed.
- **Tool-call audit logging** — every `search_rag`, `search_client`, and `draft_docx` invocation logged with inputs/outputs summary. Visible in React audit dashboard as expandable rows.
- **Source citations maintained** — agent's final answers must include `[N]` citations from `search_rag` results. Enforced by system prompt + post-generation validation.
- **Clarifying questions for ambiguity** — agent asks when client name or meeting date is missing. Two-turn max before fallback. Pure prompt design, no code complexity.

**Should have (differentiators) — P2 priority:**
- **Single freetext interface (no mode buttons)** — the #1 UX differentiator. Eliminates cognitive load of choosing modes. Adviser types naturally; agent figures out intent via tool selection.
- **Full tool-call audit trace** — exceeds typical "query + response" audit. Regulators can see not just what was generated, but HOW: which documents were searched, which client was looked up, which tool produced the draft.
- **Adviser edit tracking** — diff between AI draft and adviser-edited final. Activates existing unused `update_adviser_action()` code. Critical for demonstrating "human-in-the-loop" compliance to SFC.
- **Prompt versioning in audit log** — records which system prompt template was active when advice was generated. Essential for post-hoc review: "Was this before or after the prompt update?"

**Defer (v3.x+ / v4.0):**
- Session-aware context (complex state mgmt, deferred from v2.0)
- Multi-client batch briefs (power user feature — validate basics first)
- Template customization UI (admin tool, not adviser-facing)
- Real CRM integration (requires external agreements, data mapping)
- Agent confidence scoring
- Multi-language support (Cantonese/Mandarin queries)

**Anti-features explicitly rejected:**
- Explicit mode buttons (adds cognitive load, same v2.0 mistake)
- LangGraph or heavy agent framework (v2.0 already failed)
- Real-time CRM integration (premature for v3.0)
- Multi-LLM routing (adds complexity, negligible cost savings at this scale)
- Auto-sending drafts to clients (violates SFC human-review requirement)
- Open-ended internet search (destroys compliance boundary)
- Streaming .docx generation (technically impossible — .docx is a zip of XML files)
- Agent memory across Telegram sessions (deferred to v4.0)

### Architecture Approach

The architecture extends the existing FastAPI + Telegram bot monolith with a new `AgentService` that orchestrates the tool loop. The pattern is: Telegram handler → AgentService.run() → while-loop (LLM ↔ tools) → final answer → Telegram reply with optional .docx + inline keyboard.

**Major components:**
1. **AgentService (NEW)** — manages the while-loop: sends messages to DeepSeek V4 Pro, inspects `tool_calls`, executes tools via `ToolRegistry`, logs each call via `AuditService`, returns final answer or draft path. Pure `AsyncOpenAI` client — no framework.
2. **ToolRegistry (NEW)** — holds tool definitions (OpenAI-compatible JSON schemas) and execution functions. Maps tool names (`search_rag`, `search_client`, `draft_docx`) to async callables. Single source of truth for what the agent can do.
3. **Three tool wrappers (NEW)** — `search_rag_tool` wraps existing `query_service.process_query()`, `search_client_tool` wraps `ClientDataStore.search()`, `draft_docx_tool` wraps `docx_builder.build_*_docx()`. Each tool is a thin adapter — core logic lives in existing services.
4. **ClientDataStore (NEW abstract class)** — `abc.ABC` with `search(advisor_id, client_name) -> ClientProfile`. Mock JSON implementation for v3.0. Future DB/CRM implementation swaps in without changing agent tool code.
5. **docx_builder (EXISTING, extended)** — added `build_followup_docx()` alongside existing `build_brief_docx()`. Both create from scratch (no template files), set headers/footers, save to `/data/drafts/`.
6. **AuditService + AuditLog (EXISTING, extended)** — new columns: `tool_calls` (JSON array of tool call traces), `prompt_version` (string). New method: `log_tool_call()`. Audit writes use `BackgroundTasks` to never block the agent loop.
7. **AgentPromptManager (NEW)** — loads versioned prompt templates from `backend/prompts/`. Returns prompt string + version tag. Git-tracked files, not hardcoded strings.
8. **Telegram agent_handler + callback_handler (NEW)** — replaces existing `handle_query`. Invokes agent loop, sends result + .docx + inline keyboard. Callback handler manages approve/edit/discard actions.

**Key patterns:**
- **Tool Definition Schema:** Each tool is an OpenAI-compatible function schema with descriptions that guide LLM tool selection. Not a separate classification step — the LLM decides by reading descriptions.
- **Agent Tool Loop (While-Not-Done):** Simple loop with `MAX_TOOL_TURNS=5`. Each iteration: call LLM with tools + messages → if `tool_calls`, execute and append results → if `content` (no tool_calls), return final answer. Idempotency check prevents redundant calls.
- **ClientDataStore Abstraction:** Clean interface ensures the agent tool code is CRM-agnostic. Mock implementation for v3.0, production implementation for v4.0.

**Anti-patterns explicitly avoided:**
- Agent framework overuse (LangGraph/LangChain — v2.0 failure proven)
- Mode classification as separate step (LLM tool-calling replaces it)
- Blocking audit writes (use `BackgroundTasks`/`asyncio.create_task()`)
- Hardcoded prompts in agent code (load from versioned files)

### Critical Pitfalls

1. **Agent Tool-Call Loop Runaway** — LLM calls tools indefinitely, user waits forever. _Prevention:_ Hard max 5 turns, idempotency check (skip if same tool+args already called this turn), 60-second timeout, system prompt instruction to finalize after sufficient info. _Detection:_ Monitor `tool_calls_made` per audit entry; alert if average > 4.

2. **Source Citation Breakage in Agent Mode** — Agent paraphrases RAG output without preserving `[N]` markers. Compliance failure. _Prevention:_ System prompt enforces citation preservation ("MUST preserve `[N]` markers"), post-generation validation (flag if `search_rag` was called but no `[N]` in output), tool output format embeds citations in text that's hard to strip.

3. **Prompt Injection via Client Data** — Adversarial text in client profiles interpreted as LLM instructions. _Prevention:_ Context wrapping markers (`<client_profile>...</client_profile>`), data sanitization (strip system-prompt-like patterns), internal-only deployment limits attack surface. _Detection:_ Monitor for responses that deviate from compliance tone or drop citations unexpectedly.

4. **.docx Header/Footer Lost on Save/Load** — DRAFT disclaimer missing when opened in Word/LibreOffice. Compliance risk of unmarked draft sent to client. _Prevention:_ Always create `Document()` from scratch (already done), set header/footer AFTER all section properties, post-save validation (re-open file, assert header/footer text matches expected), test with actual Word and LibreOffice.

5. **DeepSeek V4 Pro Tool Selection Errors on Ambiguous Queries** — Agent calls `draft_docx` without first calling `search_client` (missing client name). Agent guesses client when partial match returns multiple results. _Prevention:_ System prompt enforces tool call sequence ("To prepare a meeting brief: (1) search_client, (2) search_rag if needed, (3) draft_docx"), `draft_docx` parameter validation rejects empty client_name, `search_client` returns `needs_clarification: true` when ambiguous — agent must ask user.

## Implications for Roadmap

Based on research, the suggested phase structure follows dependencies: the agent loop is useless without tools, tools are useless without delivery, and compliance hardening must be layered on a working end-to-end flow.

### Phase 1: Agent Core + End-to-End Skeleton
**Rationale:** The agent tool loop is the foundation — everything else depends on it. All three tools must be built together because the agent's value proposition (freetext → QA/brief/follow-up) requires all three to demonstrate intent routing. Without `draft_docx`, the agent can't show brief/follow-up differentiation. Without `search_client`, it can't personalize. This phase proves the architecture works end-to-end (query → tool calls → response) before investing in delivery UX and compliance hardening.
**Delivers:** Working agent that can answer product questions (QA mode), look up clients (client lookup), produce .docx drafts (brief + follow-up), all from a single freetext interface. Basic audit logging (without tool-call trace). Integration with Telegram handler for text responses.
**Addresses:** Freetext intent routing, search_rag tool, search_client tool, draft_docx tool (basic), source attribution maintenance, clarifying questions (basic prompt design).
**Avoids:** Tool-loop runaway (build with max-turns from day 1), agent framework overuse (pure while-loop, not LangGraph), mode classification (LLM tool selection only).
**Research flags:** DeepSeek V4 Pro tool-calling reliability on Hong Kong financial queries needs real-world testing. System prompt quality is the primary development variable — expect prompt iteration to be the main activity in this phase.

### Phase 2: Drafting Pipeline + Telegram Delivery
**Rationale:** The .docx drafting pipeline has its own complexity (two templates, headers/footers, file management) and integrates with Telegram delivery (send_document, inline keyboard). This is the "last mile" that makes the agent useful to advisers — without it, they can't get the .docx files. Separating from Phase 1 keeps the agent core deliverable clean.
**Delivers:** Professional .docx meeting briefs and follow-up notes with distinct headers ("CopInvest | Meeting Brief | {client}" / "CopInvest | Follow-Up Note | {client}") and DRAFT disclaimer footers. Telegram file delivery with inline keyboard [Approve] [Edit] [Discard]. Draft file storage in `/data/drafts/` with unique naming (timestamp + random suffix). Message truncation for Telegram's 4096-char limit.
**Addresses:** .docx with distinct headers/footers, .docx saved to /draft/ directory, .docx sent via Telegram, inline keyboard for approve/edit/discard, Telegram message truncation for long answers.
**Avoids:** .docx header/footer loss (post-save validation, create from scratch, no template files), Telegram message size truncation (sources in .docx, not inline text), .docx file naming collisions (add random hex suffix).
**Research flags:** .docx rendering validation across Word, LibreOffice, and other viewers — test with real applications. Inline keyboard expiry handling (stale callbacks when message is old).

### Phase 3: Audit & Compliance Hardening
**Rationale:** Compliance features (tool-call trace, prompt versioning, edit tracking, citation validation) are additive to a working system. They must be built on a stable agent pipeline, not in parallel with it. This phase transforms the prototype into an SFC-auditable system.
**Delivers:** Full tool-call audit trace (every search_rag, search_client, draft_docx invocation logged as JSON on AuditLog). Prompt versioning (version tag from template file recorded per audit entry). Adviser edit tracking (diff between AI draft and adviser-edited final). Source citation post-generation validation (flag if search_rag was called but no [N] markers). React audit dashboard extension (expandable tool-call trace view).
**Addresses:** Tool-call audit logging, prompt versioning, adviser edit tracking, source citation validation, React audit dashboard extension.
**Avoids:** Audit log JSON bloat (truncate outputs to 500 chars, paginated UI, archive policy), blocking audit writes (BackgroundTasks/asyncio.create_task), hardcoded prompts (versioned .txt files only).
**Research flags:** React audit dashboard UX for expandable JSON tool-call traces — may need UI prototyping. JSON column query performance at scale (>1K audit entries) — monitor and plan for migration to separate table if needed.

### Phase 4: Production Hardening
**Rationale:** Edge cases, safeguards, and hardening that prevent field failures. Best addressed after the full system works, because hardening decisions depend on observed behavior from Phases 1-3.
**Delivers:** Agent loop runaway safeguards (idempotency check, 60s timeout, finalize-on-max-turns message). Prompt injection defenses (data sanitization, context wrapping markers). .docx post-save header/footer validation. Client name matching improvements (return match_count, ask user when ambiguous). DeepSeek API rate limiting handling (retry with backoff). File naming collision fix (add random hex suffix). Stale inline keyboard handling (check audit status on callback).
**Addresses:** All critical/moderate pitfall mitigations, edge case handling, observability improvements.
**Avoids:** All pitfalls from PITFALLS.md that require runtime hardening.
**Research flags:** Prompt injection surface area with real client data — needs adversarial testing. Agent loop behavior on edge-case queries — needs fuzz testing with diverse Hong Kong financial query patterns.

### Phase Ordering Rationale

- **Dependencies drive ordering:** Agent loop → Tools → Delivery → Compliance. The agent loop must exist before tools can be registered. Tools must be registered before drafting can be demonstrated. Drafting must work before delivery UX makes sense. Compliance audit features layer on a stable system.
- **Rapid validation:** Phase 1 proves the architecture with minimal investment. If DeepSeek V4 Pro tool-calling doesn't meet reliability needs, the approach can pivot before investing in delivery and compliance.
- **Risk layering:** Critical pitfalls (loop runaway, citation breakage) are addressed in Phase 1 design. Moderate pitfalls (tool selection errors, Telegram limits) are addressed in Phase 2. Minor pitfalls are deferred to Phase 4 hardening.
- **Incremental shippability:** Each phase produces a testable increment. Phase 1 = working QA agent. Phase 2 = working drafting agent. Phase 3 = auditable drafting agent. Phase 4 = production-ready agent.

### Research Flags

**Phases likely needing deeper research during planning (`/gsd-research-phase`):**
- **Phase 1:** Prompt engineering for intent routing — the system prompt IS the product. Needs experimentation with Hong Kong financial adviser query patterns, tool selection accuracy measurement, and citation preservation reliability. **This is the highest-risk phase for research investment.**
- **Phase 2:** .docx cross-application rendering validation. python-docx behavior differs across Word, LibreOffice, Pages, and online viewers. Header/footer rendering is especially fragile. Needs systematic testing matrix.
- **Phase 3:** React audit dashboard UX for tool-call trace. Expandable JSON data in a compliance-facing interface has non-trivial UX requirements. Users (compliance officers) need to quickly assess tool call quality, not read raw JSON.

**Phases with standard patterns (skip research-phase, proceed to implementation):**
- **Phase 1 tool wrappers:** Well-documented. The three tools are thin adapters over existing code. Standard OpenAI tool definition schema. No research needed.
- **Phase 2 Telegram delivery:** `send_document()` and `InlineKeyboardButton` are well-documented in python-telegram-bot. Standard patterns. No research needed.
- **Phase 3 audit logging extensions:** JSON column on existing SQLAlchemy model. Standard migration pattern. No research needed.
- **Phase 4 hardening:** Standard defensive programming patterns. No research needed — implement pitfall mitigations from PITFALLS.md directly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies are existing dependencies or official SDKs. DeepSeek API docs confirmed. python-docx behavior verified against existing codebase. No speculative stack choices. |
| Features | HIGH | Feature list grounded in PROJECT.md scope, v2.0 failure analysis, and competitor gap analysis. Table stakes derived from adviser workflow analysis. Anti-features explicitly rejected with documented rationale. |
| Architecture | HIGH | Agent loop pattern is standard (OpenAI tool-calling docs). All components map to existing codebase or clean extensions. Anti-patterns validated by v2.0 failure experience. Component boundaries are clean and testable. |
| Pitfalls | MEDIUM | Pitfall categories are well-known (tool loop runaway, prompt injection, citation breakage) but their specific interactions in a Hong Kong financial adviser context need phase-level testing. Docx rendering and Telegram integration pitfalls are practical rather than theoretical — need real-world validation. |

**Overall confidence:** MEDIUM-HIGH

The individual pieces are well-understood and well-documented. The integration of prompt-driven agent + tool calling + compliance audit in a regulated environment has unknowns that need phase-level testing, particularly around:
- DeepSeek V4 Pro tool-calling reliability on Hong Kong financial queries
- System prompt quality for intent routing with real adviser language patterns
- Citation preservation across the agent's tool→generation boundary
- .docx rendering consistency across word processors used in Hong Kong firms

### Gaps to Address

- **Agent tool-calling accuracy on Hong Kong adviser queries:** Research provides strong theoretical basis (DeepSeek V4 Pro's 80.6% SWE-Bench score) but lacks empirical data on financial adviser intent routing specifically. _Handle during Phase 1 execution: instrument tool selection accuracy, collect failure patterns, iterate prompt._
- **System prompt optimization workflow:** The prompt-driven agent approach means prompt quality = product quality. Research identifies this as critical but doesn't provide the prompt itself. _Handle during Phase 1: start with a draft prompt based on tool definitions, iterate based on observed behavior, version every iteration._
- **Citation preservation reliability:** Research identifies the mechanism (system prompt enforcement + post-generation validation) but doesn't quantify reliability. _Handle during Phase 1: build automated test suite that verifies citations survive the agent pipeline end-to-end._
- **.docx cross-application rendering:** python-docx header/footer behavior across Word, LibreOffice, and other viewers is not fully characterized. _Handle during Phase 2: build a rendering test matrix, validate across all applications used by target advisers._
- **Audit dashboard UX for compliance users:** Expandable JSON tool-call traces in a React UI has UX unknowns. Compliance officers need to quickly assess tool call quality, not read raw JSON. _Handle during Phase 3: prototype with actual compliance user feedback, iterate presentation format._
- **Prompt injection surface with real Hong Kong client data:** Research identifies the vulnerability class but mock data doesn't represent real-world adversarial scenarios. _Handle during Phase 4: test with diverse client profile data, including edge cases with special characters, long text, and instruction-like patterns._

## Sources

### Primary (HIGH confidence)
- DeepSeek API — Function Calling docs: https://api-docs.deepseek.com/guides/function_calling — tool definitions, tool_calls response format, multi-turn examples
- DeepSeek API — Tool Calls guide: https://api-docs.deepseek.com/guides/tool_calls — Python examples, tool result appending
- DeepSeek API — Chat Completion parameters: https://api-docs.deepseek.com/api/create-chat-completion — tools, tool_choice, response schema
- DeepSeek V4 Pro model card: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro — agentic benchmarks, reasoning modes
- python-docx — Header/Footer API: https://github.com/python-openxml/python-docx/blob/master/docs/dev/analysis/features/header.rst — section header/footer manipulation
- python-docx — User guide (sections, headers, footers): https://github.com/python-openxml/python-docx/blob/master/docs/user/hdrftr.rst — creation patterns, inheritance behavior
- CopInvest codebase — `backend/services/query_service.py`, `docx_builder.py`, `audit_service.py`, `models/audit_log.py`, `telegram_bot/handlers.py` — existing architecture, patterns, unused code paths
- CopInvest PROJECT.md — v3.0 milestone scope, v2.0 failures documented, Out of Scope decisions

### Secondary (MEDIUM confidence)
- DeepSeek V4 Pro review — 80.6% SWE-Bench Verified: https://www.mindstudio.ai/blog/deepseek-v4-open-source-frontier-model-review — third-party validation, corroborated by official model card
- OpenAI — Tool calling best practices: https://platform.openai.com/docs/guides/function-calling — shared patterns (max turns, validation, prompt design)
- CopInvest CLAUDE.md — project constraints, tech stack baseline, conventions

### Tertiary (LOW confidence)
- Prompt injection in RAG systems — general knowledge (well-established vulnerability pattern, no CopInvest-specific research found)
- Hong Kong SFC audit requirements — inferred from project scope, not directly researched as primary source

---

*Research completed: 2026-05-13*
*Ready for roadmap: yes*
