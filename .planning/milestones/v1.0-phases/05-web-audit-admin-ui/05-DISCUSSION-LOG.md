# Phase 5: Web Audit & Admin UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 05-web-audit-admin-ui
**Areas discussed:** Audit log table design, Ingestion UI flow, Auth and access model

---

## Audit Log Table Design

| Option | Description | Selected |
|--------|-------------|----------|
| Compact: 6 columns | timestamp, user, channel, query (truncated), status, adviser action | ✓ |
| Detailed: 8 columns | + sensitivity tier, model used | |
| Minimal: 4 columns | timestamp, user, query, adviser action only | |

**Filtering:**

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side filtering | Filters sent to backend on each change | ✓ |
| Client-side filtering | Load all, filter in browser | |

**Pagination:**

| Option | Description | Selected |
|--------|-------------|----------|
| Pagination | Standard prev/next page controls | ✓ |
| Infinite scroll | Load more as you scroll | |

**Row click:**

| Option | Description | Selected |
|--------|-------------|----------|
| Navigate to trace page | /audit/:trace_id — full page, shareable URL | ✓ |
| Expand inline | Panel below the row | |
| Slide-over panel | Right-side panel, list stays visible | |

**Notes:** No additional questions — user moved to next area.

---

## Ingestion UI Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Single form | File picker + tier dropdown + submit | ✓ |
| Two-step wizard | Upload then assign tier | |

**Feedback during upload:**

| Option | Description | Selected |
|--------|-------------|----------|
| Spinner + inline result | Show IngestResponse on success | ✓ |
| Fake progress bar | Animated fill, no real progress | |
| Submit and redirect | Navigate to document registry | |

**Result display:**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline result, form stays | Result below form, can submit again | ✓ |
| Toast + form reset | Notification, form clears | |
| Modal with full details | Modal showing IngestResponse | |

**Notes:** Endpoint is synchronous — may take 30-60s for large PDFs. Spinner must handle long waits.

---

## Auth and Access Model

| Option | Description | Selected |
|--------|-------------|----------|
| Own login page | /login calls POST /api/v1/auth/login | |
| No login — assume pre-authenticated | JWT read from localStorage, set externally | ✓ |
| External auth provider | Auth0, Supabase Auth, etc. | |

**Role access:**

| Option | Description | Selected |
|--------|-------------|----------|
| All roles see everything | No per-view restrictions in frontend | ✓ |
| Role-based view access | Compliance: audit only; Admin: all views | |
| Compliance sees all, ingestion disabled | Grayed out for compliance | |

**Token storage:**

| Option | Description | Selected |
|--------|-------------|----------|
| localStorage JWT | Simple, works with existing token pattern | ✓ |
| httpOnly cookie | More secure, requires CORS + cookie config | |

**Notes:** Internal admin tool — localStorage acceptable. Backend require_role() enforces access at API layer.

---

## Claude's Discretion

- Trace inspector layout (collapsible sections vs flat scroll vs side-by-side)
- Document registry filtering/sorting
- Navigation shell style (sidebar vs top nav)
- Empty state designs
- Error state handling
- Date picker component choice

## Deferred Ideas

None.
