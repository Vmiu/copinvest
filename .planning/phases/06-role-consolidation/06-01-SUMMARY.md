---
phase: 06-role-consolidation
plan: "01"
subsystem: auth
tags: [alembic, rbac, userrole, sqlite, postgresql]

requires: []
provides:
  - UserRole.admin enum member replacing UserRole.compliance
  - Alembic migration b9c4d2e1f3a7 upgrading DB rows compliance→admin
  - All require_role() call sites passing "admin" (6 sites across 4 routers)
  - TIER_TO_ROLES mapping all tiers to "admin" (5 occurrences in ingestion_service)
affects: [06-02, 06-03, tests]

tech-stack:
  added: []
  patterns:
    - "Dialect-conditional Alembic migration: SQLite UPDATE-only, PostgreSQL full enum recreation"

key-files:
  created:
    - alembic/versions/b9c4d2e1f3a7_rename_compliance_to_admin.py
  modified:
    - backend/models/enums.py
    - backend/routers/audit.py
    - backend/routers/ingest.py
    - backend/routers/documents.py
    - backend/routers/query.py
    - backend/services/ingestion_service.py

key-decisions:
  - "compliance → admin rename: admin is the correct concept for dashboard/doc management access; compliance was a misnomer"

patterns-established:
  - "Dialect-conditional migration: use op.get_bind().dialect.name to branch SQLite vs PostgreSQL logic"

requirements-completed: [ROLE-01]

duration: 6min
completed: "2026-05-11"
---

# Phase 6 Plan 01: Role Consolidation — Backend Migration Summary

**Alembic migration b9c4d2e1f3a7 renames compliance→admin in SQLite/PostgreSQL; UserRole enum and all 6 require_role() call sites updated atomically**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-11T04:32:51Z
- **Completed:** 2026-05-11T04:38:45Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created dialect-conditional Alembic migration (SQLite: UPDATE only; PostgreSQL: full enum recreation with IF NOT EXISTS guard)
- Migration applied to dev SQLite DB — `alembic current` shows `b9c4d2e1f3a7 (head)`
- Replaced `UserRole.compliance` with `UserRole.admin` in enums.py; `UserRole.compliance` no longer exists
- Updated all 6 `require_role()` call sites: audit.py (×3), ingest.py, documents.py, query.py
- Updated TIER_TO_ROLES dict (4 tier entries) and fallback (1) in ingestion_service.py

## Task Commits

1. **Task 1: Create Alembic migration** — `47d2c36` (chore)
2. **Task 2: Update Python enum and all backend call sites** — `ccf76bc` (feat)

## Files Created/Modified

- `alembic/versions/b9c4d2e1f3a7_rename_compliance_to_admin.py` — dialect-conditional migration, down_revision=a1b2c3d4e5f6
- `backend/models/enums.py` — UserRole.compliance → UserRole.admin
- `backend/routers/audit.py` — 3× require_role("compliance") → require_role("admin")
- `backend/routers/ingest.py` — require_role("compliance") → require_role("admin")
- `backend/routers/documents.py` — require_role("compliance") → require_role("admin")
- `backend/routers/query.py` — require_role("adviser","senior_adviser","compliance") → require_role("adviser","senior_adviser","admin")
- `backend/services/ingestion_service.py` — TIER_TO_ROLES dict + fallback (5 occurrences)

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Backend Python is internally consistent: `UserRole.compliance` does not exist, zero stray `"compliance"` role strings in backend Python (excluding generation_service.py prose)
- Plan 06-02 (frontend label updates) and Plan 06-03 (test updates) can proceed
- Tests referencing `"compliance"` role will fail until Plan 06-03 updates them — expected, documented in plan

---
*Phase: 06-role-consolidation*
*Completed: 2026-05-11*
