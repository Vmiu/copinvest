---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: v3.0 Agent Workflows & Drafting Pipelines
status: planning
last_updated: "2026-05-13T00:00:00.000Z"
last_activity: 2026-05-13
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-13)

**Core value:** Advisers can ask a question and get an accurate, source-attributed answer from approved internal documents — with every interaction fully auditable.
**Current focus:** v3.0 Agent Workflows & Drafting Pipelines — prompt-driven agent + .docx drafting + compliance audit extensions

## Current Position

Phase: 8 — Agent Framework + RAG Tool + Audit Schema
Plan: —
Status: Roadmap defined (4 phases, 21 requirements)
Last activity: 2026-05-13 — Roadmap created for v3.0

## v3.0 Phases

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 8. Agent Framework + RAG + Audit Schema | Freetext agent routes to QA/chat, cites sources, audit schema ready | 7 (AGENT-01–03,05–07, AUDIT-01) | Not started |
| 9. Client Lookup + Docx Drafting | Client search + meeting brief/follow-up .docx with headers/footers | 9 (AGENT-04, CLIENT-01–03, DOCX-01–05) | Not started |
| 10. Audit Dashboard — Tool Call Visibility | Expandable tool-call trace in React audit dashboard | 2 (AUDIT-02–03) | Not started |
| 11. Telegram Integration | Agent routing, .docx delivery, user→advisor_id linking | 3 (TELE-01–03) | Not started |

## Performance Metrics

**Velocity (v1.0 baseline):**
- Total plans completed: 17
- Average duration: ~5min
- Total execution time: ~1.5 hours

**Velocity (v2.0):**
- Total plans completed: 7
- Total execution time: ~0.5 hours

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Qdrant over ChromaDB — pre-filtering enforces RBAC at DB layer (security-correct model)
- Roadmap: Audit trail and RBAC in Phase 1 — SFC regulatory requirement, not optional
- Roadmap (revised 2026-04-29): Telegram is the PRIMARY adviser interface — full Q&A, draft review flow (Approve/Edit/Discard inline keyboard), and action tracking in audit trail
- Roadmap (revised 2026-04-29): React web UI is an audit/admin dashboard only — audit log viewer, trace inspector, document registry, admin ingestion; not a chat interface
- v2.0 roadmap: compliance → admin rename is Phase 6 (own phase)
- v2.0 roadmap: META-01 is Phase 7 (own phase)
- v2.0 roadmap: Phases 8–10 (Agent Framework, Drafting Pipelines, Audit Hardening) deferred to next milestone — needs workflow redesign
- v3.0 roadmap: Prompt-driven agent (no LangGraph/agent framework) — v2.0 LangGraph approach abandoned as "messy/unsatisfying"
- v3.0 roadmap: AGENT requires AUDIT schema first — tool_calls JSON column must exist before agent writes to it; AUDIT-01 placed in Phase 8
- v3.0 roadmap: CLIENT and DOCX developed together in Phase 9 — tools can be built in parallel behind abstract interface
- v3.0 roadmap: TELE is final phase — agent's value is unlocked by Telegram integration; all previous phases work through API
- v3.0 roadmap: python-docx is already in pyproject.toml (v1.0 dependency); no new package installations required
- v3.0 roadmap: DOCX builders wrap in asyncio.to_thread() from first implementation (DOCX-04)

### Pending Todos

None.

### Blockers/Concerns

None.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Compliance | COMP-01: investment advice detection | v4.0 | 2026-05-11 |
| Compliance | COMP-02: faithfulness scoring | v4.0 | 2026-05-11 |
| Agent | SESS-01: session-aware intent routing | v4.0 | 2026-05-11 |
| Audit | AUDIT-V4-01: prompt versioning | v4.0 | 2026-05-13 |
| Audit | AUDIT-V4-02: adviser edit tracking | v4.0 | 2026-05-13 |
| Audit | AUDIT-V4-03: immutable append-only with 7-year retention | v4.0 | 2026-05-13 |
| Audit | AUDIT-V4-04: compliance guardrail layer | v4.0 | 2026-05-13 |

## Session Continuity

Last session: 2026-05-13
Stopped at: v3.0 roadmap created (4 phases, 21 requirements mapped)
Resume file: None
Next action: `/gsd-plan-phase 8` to begin Agent Framework + RAG Tool + Audit Schema
