---
phase: 06-role-consolidation
plan: "02"
subsystem: qdrant, seed-data, frontend
tags: [qdrant, migration, rbac, seed, login]

requires:
  - 06-01 (UserRole.admin enum + backend call sites)
provides:
  - scripts/migrate_qdrant_roles.py — one-time Qdrant payload migration script
  - backend/seed_users.json carol entry updated to role "admin" / password "admin123"
  - frontend/src/pages/LoginPage.tsx constants renamed ADMIN_EMAIL / ADMIN_PASSWORD
affects: []

tech-stack:
  added: []
  patterns:
    - "Qdrant scroll+overwrite_payload pagination loop for bulk payload updates"

key-files:
  created:
    - scripts/migrate_qdrant_roles.py
  modified:
    - backend/seed_users.json
    - frontend/src/pages/LoginPage.tsx

key-decisions:
  - "migrate_qdrant_roles.py uses overwrite_payload scoped to points=[point.id] — only touches allowed_roles, no other payload fields modified (T-06-04)"

duration: 5min
completed: "2026-05-11"
---

# Phase 6 Plan 02: Role Consolidation — Qdrant Migration + Seed + Frontend Summary

**Qdrant scroll+overwrite_payload migration script created; seed carol entry and LoginPage constants updated from compliance to admin**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-05-11
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `scripts/migrate_qdrant_roles.py` — scrolls all Qdrant points (100/page), replaces `"compliance"` with `"admin"` in `allowed_roles` payloads via `overwrite_payload`
- Updated carol's seed entry: `"role": "compliance"` → `"role": "admin"`, `"password": "compliance123"` → `"password": "admin123"`
- Renamed `COMPLIANCE_EMAIL`/`COMPLIANCE_PASSWORD` → `ADMIN_EMAIL`/`ADMIN_PASSWORD` in LoginPage.tsx; updated all usages

## Task Commits

1. **Task 1: Create Qdrant role migration script** — `1733570` (feat)
2. **Task 2: Update seed data and frontend login constants** — `f9a34cb` (feat)

## Files Created/Modified

- `scripts/migrate_qdrant_roles.py` — pagination loop with scroll+overwrite_payload, CLI args --collection/--url with env var defaults
- `backend/seed_users.json` — carol: role admin, password admin123
- `frontend/src/pages/LoginPage.tsx` — COMPLIANCE_* constants renamed to ADMIN_*

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints or auth paths introduced. Migration script has no user input flowing into payload values (T-06-04 mitigated).

## Self-Check: PASSED

- `scripts/migrate_qdrant_roles.py` — FOUND
- `backend/seed_users.json` — FOUND, 0 "compliance" occurrences
- `frontend/src/pages/LoginPage.tsx` — FOUND, 0 COMPLIANCE_ occurrences
- Commit `1733570` — FOUND
- Commit `f9a34cb` — FOUND

---
*Phase: 06-role-consolidation*
*Completed: 2026-05-11*
