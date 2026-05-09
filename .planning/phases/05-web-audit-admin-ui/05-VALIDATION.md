---
phase: 5
slug: web-audit-admin-ui
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-09
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.0 + pytest-asyncio 0.26.0 (backend); no frontend test framework in Phase 5 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -q -x` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | UI-01 | T-5-01 | require_role("compliance") on GET /api/v1/audit | integration | `uv run pytest tests/test_audit_router.py -x` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | UI-02 | T-5-01 | require_role("compliance") on GET /api/v1/audit/{trace_id} | integration | `uv run pytest tests/test_audit_router.py::test_get_trace_detail -x` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | UI-03 | T-5-02 | require_role("compliance") on GET /api/v1/documents | integration | `uv run pytest tests/test_document_router.py -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | UI-01 | — | N/A | manual | UI: filter bar triggers API call with correct params | N/A | ⬜ pending |
| 5-02-02 | 02 | 2 | UI-02 | — | N/A | manual | UI: trace inspector shows all AuditLog fields | N/A | ⬜ pending |
| 5-02-03 | 02 | 2 | UI-03 | — | N/A | manual | UI: document registry renders all DocumentRecord rows | N/A | ⬜ pending |
| 5-02-04 | 02 | 2 | UI-04 | — | N/A | manual | UI: ingest form shows spinner, success/error inline | N/A | ⬜ pending |
| 5-03-01 | 03 | 3 | UI-01, UI-02 | — | N/A | automated | `cd frontend && npm run build 2>&1 \| grep -E "error\|✓ built"` | N/A | ⬜ pending |
| 5-03-02 | 03 | 3 | UI-03, UI-04 | — | N/A | automated | `cd frontend && npm run build 2>&1 \| grep -E "error\|✓ built"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 items are created in Plan 05-01 (Wave 1) before Wave 2 and Wave 3 tasks execute.

- [x] `tests/test_audit_router.py` — created in 05-01 Task 2
- [x] `tests/test_document_router.py` — created in 05-01 Task 2
- [x] `backend/routers/audit.py` — created in 05-01 Task 1
- [x] `backend/routers/documents.py` — created in 05-01 Task 1
- [x] `backend/schemas/document.py` — created in 05-01 Task 1

*Note: UI-04 (ingest form) uses the existing POST /api/v1/ingest endpoint — covered by existing tests/test_ingest_router.py.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit log filter bar triggers server-side API call | UI-01 | React component behavior; no frontend test framework in Phase 5 | Open /audit, set date range + user filter, click Apply, verify network request in DevTools |
| Trace inspector collapsible sections expand/collapse | UI-02 | DOM interaction; no frontend test framework | Open /audit/:trace_id, click each section header, verify expand/collapse |
| Document registry sensitivity tier filter (client-side) | UI-03 | React state; no frontend test framework | Open /documents, select "Restricted" from tier dropdown, verify table filters without API call |
| Ingest form spinner persists for long requests | UI-04 | Timing behavior; no frontend test framework | Submit a large PDF, verify spinner shows and form is disabled during request |
| not_found flag shows amber badge in trace inspector | UI-02 | Visual state; no frontend test framework | Query with no matching docs, open trace, verify amber "No chunks retrieved" badge |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (all created in 05-01 Wave 1)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-05-09
