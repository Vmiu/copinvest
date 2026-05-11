---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: v2.0 Agent Skills & Audit Hardening
status: ready
stopped_at: Phase 6 complete — compliance→admin rename done, 85 tests passing
last_updated: "2026-05-11T04:41:56Z"
last_activity: 2026-05-11
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-11)

**Core value:** Advisers can ask a question and get an accurate, source-attributed answer from approved internal documents — with every interaction fully auditable.
**Current focus:** v2.0 — Phase 6: Role Consolidation (compliance → admin rename)

## Current Position

Phase: 6 of 10 (Role Consolidation) — COMPLETE
Plan: 3 of 3
Status: Phase 6 complete — ready for Phase 7
Last activity: 2026-05-11

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity (v1.0 baseline):**

- Total plans completed: 17
- Average duration: ~5min
- Total execution time: ~1.5 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-data-foundation | 4 | 17min | 4.3min |
| 02-document-ingestion | 4 | 28min | 7min |
| 03-rag-query-pipeline | 3 | — | — |
| 04-telegram-bot | 3 | — | — |
| 05-web-audit-ui | 3 | — | — |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Qdrant over ChromaDB — pre-filtering enforces RBAC at DB layer (security-correct model)
- Roadmap: Audit trail and RBAC in Phase 1 — SFC regulatory requirement, not optional
- Roadmap (revised 2026-04-29): Telegram is the PRIMARY adviser interface — full Q&A, draft review flow (Approve/Edit/Discard inline keyboard), and action tracking in audit trail
- Roadmap (revised 2026-04-29): React web UI is an audit/admin dashboard only — audit log viewer, trace inspector, document registry, admin ingestion; not a chat interface
- 01-01: Used get_settings() factory with lru_cache for testable config without hardcoded secrets
- 01-01: AuditLog uses progressive lifecycle fields (status enum tracks received→retrieved→generated→completed)
- 01-02: Used pwdlib BcryptHasher explicitly (not PasswordHash.recommended()) for deterministic hasher selection
- 01-02: Added GET /api/v1/auth/me as protected test endpoint for verifying token-based access
- 01-02: Alembic async env.py reads DB URL from get_settings() (not hardcoded in alembic.ini)
- 01-03: Used db.flush() in service functions (not commit) -- caller controls transaction boundary
- 01-03: Normalized datetime comparison to naive UTC for SQLite compatibility
- 01-04: RBAC filtering uses single MatchValue on allowed_roles -- Qdrant pre-filters before ANN search
- 01-04: Lifespan wraps Qdrant init in try/except so app starts without Docker running
- 02-01: openai_api_key has no default — forces explicit env config, never logged (T-02-05)
- 02-01: upsert_chunks generates UUID point IDs — avoids ID conflicts across re-ingestion cycles
- 02-01: require_role(*roles) factory pattern for role-based endpoint protection
- 02-02: AsyncOpenAI client injected as parameter in chunking/embedding services — no get_settings() in service modules (testability, D-01)
- 02-02: openai>=1.68.0 added to pyproject.toml — was missing from declared dependencies
- 02-03: TIER_TO_ROLES maps SensitivityTier members to allowed_roles lists — Qdrant payload enforces RBAC pre-filtering at ingestion time
- 02-03: delete_by_source before upsert — idempotent re-ingestion replaces existing chunks (D-12)
- 02-03: docling parse runs in asyncio.to_thread() — CPU-bound operation never blocks event loop
- 02-04: current_user["user_id"] not "sub" — get_current_user() returns {"user_id": ..., "role": ...} not JWT claims directly
- 02-04: setup_collection() required in qdrant_memory fixture — in-memory Qdrant starts with no collections
- 02-04: ingested_at excluded from upsert update path — SQLAlchemy lambda default only fires on INSERT, not on Python object copy
- 05-02: React pinned to ^18.3.1 — Vite scaffold installs React 19 by default
- 05-02: Page components use lazy() — App.tsx compiles without page implementations; stubs replaced in Plan 05-03
- v2.0 roadmap: compliance → admin rename is Phase 6 (own phase) — touches DB migration, enums, all require_role() call sites, frontend labels
- v2.0 roadmap: META-01 is Phase 7 (own phase) — requires Qdrant payload schema change + DB migration + full re-ingestion
- v2.0 roadmap: LangGraph + MCP tools + skills are Phase 8 (tightly coupled) — wraps existing services as tool nodes, minimal rewrite
- v2.0 roadmap: Drafting pipelines (BRIEF + FOLLOW + TELE scoping) are Phase 9 — depend on agent+tools from Phase 8
- v2.0 roadmap: Audit hardening + prompt versioning are Phase 10 — final hardening after pipelines are in place
- v2.0 roadmap: SFC 7-year retention confirmed as AUDIT-V2-03 requirement

### Pending Todos

None.

### Blockers/Concerns

None.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Compliance | COMP-01: investment advice detection | v3 | 2026-05-11 |
| Compliance | COMP-02: faithfulness scoring | v3 | 2026-05-11 |
| Agent | SESS-01: session-aware intent routing | v3 | 2026-05-11 |

## Session Continuity

Last session: 2026-05-11T18:35:00Z
Stopped at: v2.0 roadmap created (Phases 6–10, 19/19 requirements mapped)
Resume file: None
Next action: `/gsd-plan-phase 6`
