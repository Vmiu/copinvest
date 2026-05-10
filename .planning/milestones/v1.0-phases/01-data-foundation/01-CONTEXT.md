# Phase 1: Data Foundation - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Auth, RBAC, audit schema, and Qdrant/PostgreSQL infrastructure. Users can authenticate, roles control document access at the vector store layer, and every future query will produce a full audit record. This phase builds the security and compliance foundation that all subsequent phases depend on.

</domain>

<decisions>
## Implementation Decisions

### Infrastructure Setup
- **D-01:** SQLite for local development database (users, audit_log, doc_registry). SQLAlchemy abstracts the dialect difference from production PostgreSQL.
- **D-02:** Qdrant runs as a Docker container for local dev — same behavior as production. Use `qdrant-client` Python SDK.
- **D-03:** Development environment uses `docker-compose.yml` with Qdrant service. SQLite file lives in project directory.

### RBAC Design
- **D-04:** Three fixed roles: `adviser`, `senior_adviser`, `compliance`. No configurable roles for v1.
- **D-05:** Strict hierarchy tier mapping:
  - `adviser` → Public only (tier 1)
  - `senior_adviser` → Public + Internal + Restricted (tiers 1-3)
  - `compliance` → All tiers including Confidential (tiers 1-4)
- **D-06:** Users are seeded via a config file (JSON or YAML) — no registration UI or self-signup. Seed file contains email, hashed password, and role.
- **D-07:** Role is stored in the JWT payload so every request carries its own permission context without a DB lookup per query.

### Audit Trail Mechanics
- **D-08:** Progressive audit record lifecycle: record created when query is received (with trace_id, user_id, timestamp, query_text), updated as retrieval completes (retrieved_chunks, prompt_sent), updated again after LLM response (llm_response, model_version), final update when adviser acts in Telegram (adviser_action: approved/edited/discarded).
- **D-09:** Sessions defined by inactivity timeout (30 minutes). A session starts on first message and ends after 30 min of no activity. Each session has a session_id, start_time, and end_time. Audit records reference their session_id.
- **D-10:** Audit records include sensitivity_tier_accessed — the highest tier of any document chunk retrieved in that query.

### Claude's Discretion
- Exact SQLAlchemy model field types and indexes
- Alembic migration structure
- JWT token expiry duration and refresh strategy
- Seed file format (JSON vs YAML)
- Qdrant collection configuration (distance metric, vector size)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — AUTH-01..05, AUDIT-01..05 requirements for this phase
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, FastAPI structure, audit schema
- `.planning/research/STACK.md` — Technology choices with versions (LlamaIndex, Qdrant, FastAPI, SQLAlchemy)
- `.planning/research/PITFALLS.md` — Critical pitfalls #1 (permission filtering), #3 (audit gaps), #8 (token exposure)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
No existing code — greenfield project. Phase 1 establishes all foundational patterns.

### Established Patterns
None yet — this phase defines the patterns that subsequent phases will follow.

### Integration Points
- Qdrant metadata schema (sensitivity_tier, allowed_roles) must align with Phase 2 ingestion pipeline
- Audit log schema must support Phase 4 Telegram adviser actions (approve/edit/discard via inline keyboard)
- JWT auth middleware must work for both FastAPI web routes and Telegram webhook handler

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Research ARCHITECTURE.md has a detailed FastAPI project structure and audit log schema that can serve as the starting point.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-04-29*
