# Phase 5: Web Audit & Admin UI - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Compliance officers and admins can inspect the full audit trail, drill into individual query traces, view the document registry, and trigger ingestion — all from a React dashboard. Scope: React frontend app, new audit/document API endpoints on the FastAPI backend, navigation shell. The chat/query interface for advisers is out of scope (that is a future phase). Telegram bot is Phase 4 (complete).

</domain>

<decisions>
## Implementation Decisions

### Audit Log Table
- **D-01:** 6 columns: timestamp, user, channel (web/telegram), query (truncated), status, adviser action.
- **D-02:** Server-side filtering — filter params (user, date range, session) sent to backend on each change. Requires new `GET /api/v1/audit` endpoint with query params.
- **D-03:** Pagination (not infinite scroll) — standard prev/next page controls. Compliance officers need predictable navigation to specific date ranges.
- **D-04:** Clicking a row navigates to `/audit/:trace_id` — full trace page with shareable URL.

### Trace Inspector
- **D-05:** Full trace page at `/audit/:trace_id`. Displays all AuditLog fields: query_text, rewritten_query, retrieved_chunks (JSON), prompt_sent, llm_response, adviser_action, final_response, model_used, token counts, sensitivity_tier_accessed, channel, not_found flag.
- **D-06:** Claude's discretion on layout (collapsible sections vs flat scroll) — the data model is the constraint, not the layout.

### Ingestion UI
- **D-07:** Single form — file picker + sensitivity tier dropdown + submit button. No wizard.
- **D-08:** Spinner while request is in-flight (endpoint is synchronous, may take 30-60s for large PDFs).
- **D-09:** On success: show IngestResponse inline below the form (chunk count, warnings, document ID). Form stays — user can submit another file immediately.
- **D-10:** On error: show error message inline below the form.

### Document Registry
- **D-11:** Table listing all DocumentRecord rows: filename, doc_type, sensitivity_tier, chunk_count, ingested_at, ingested_by. Claude's discretion on filtering/sorting.

### Auth and Access Model
- **D-12:** No login page — assume pre-authenticated. The React app reads a JWT from localStorage (set externally, e.g., by a reverse proxy or dev tooling). All routes are accessible without a login flow.
- **D-13:** All admin/compliance roles see all 4 views — no per-view role restrictions in the frontend. Backend `require_role` dependency enforces access at the API layer.
- **D-14:** JWT stored in localStorage. Acceptable for an internal admin tool.

### Navigation Shell
- **D-15:** Claude's discretion on nav structure (sidebar vs top nav). Four views: Audit Log, Trace Inspector (detail only, no nav item), Document Registry, Ingest Document.

### Claude's Discretion
- Trace inspector layout (collapsible sections vs flat scroll vs side-by-side)
- Document registry filtering/sorting
- Navigation shell style (sidebar vs top nav)
- Empty state designs
- Error state handling
- Exact date picker component choice

</decisions>

<specifics>
## Specific Ideas

- The existing `POST /api/v1/ingest` endpoint is synchronous — ingestion can take 30-60s for large PDFs. The UI must handle a long-running request gracefully (spinner, no timeout).
- `AuditLog.not_found` flag should be surfaced in the trace inspector — it indicates the RAG pipeline found no relevant chunks.
- `AuditLog.rewritten_query` should be shown in the trace inspector alongside the original query — it shows what the query rewriter produced.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Web Audit & Admin UI — UI-01 through UI-04 acceptance criteria

### Data models (read before designing API endpoints)
- `backend/models/audit_log.py` — AuditLog and Session models; all fields available for the trace inspector
- `backend/models/document.py` — DocumentRecord model; fields for the document registry
- `backend/models/enums.py` — AdviserAction, AuditStatus, SensitivityTier enums

### Existing API patterns (follow these conventions)
- `backend/routers/ingest.py` — POST /api/v1/ingest; require_role pattern, UploadFile + Form params
- `backend/routers/auth.py` — JWT auth endpoint; token format
- `backend/core/dependencies.py` — require_role() dependency; get_db() pattern

### Existing repositories (extend, don't rewrite)
- `backend/repositories/audit_repo.py` — get_audit_by_id, get_audits_by_session; extend with list/filter query
- `backend/repositories/document_repo.py` — extend with list query for document registry

### Stack reference
- `CLAUDE.md` §Technology Stack — React 18, @assistant-ui/react 0.12.x, Tailwind CSS 3.x, FastAPI 0.128.x

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/core/dependencies.py` — `require_role()` FastAPI dependency; use for all new admin endpoints
- `backend/core/database.py` — `get_db()` async session dependency; use for all new endpoints
- `backend/repositories/audit_repo.py` — `get_audit_by_id`, `get_audits_by_session`; extend with paginated list + filter query
- `backend/repositories/document_repo.py` — extend with `list_documents()` for the registry view

### Established Patterns
- All routers use `APIRouter(prefix="/api/v1", tags=[...])` — new audit/document endpoints follow the same prefix
- `require_role("compliance")` or `require_role("admin")` guards sensitive endpoints — use for all Phase 5 endpoints
- `structlog.get_logger()` for structured logging — use in new routers
- Pydantic v2 response schemas in `backend/schemas/` — create new schemas for audit list response and document list response

### Integration Points
- New `GET /api/v1/audit` endpoint needed: paginated list with filters (user_id, date_from, date_to, session_id)
- New `GET /api/v1/audit/:trace_id` endpoint needed: single record detail (or reuse existing audit_repo.get_audit_by_id)
- New `GET /api/v1/documents` endpoint needed: paginated list of DocumentRecord rows
- `POST /api/v1/ingest` already exists — the ingestion UI calls it directly
- React app communicates with FastAPI via REST; JWT passed as `Authorization: Bearer <token>` header

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-web-audit-admin-ui*
*Context gathered: 2026-05-09*
