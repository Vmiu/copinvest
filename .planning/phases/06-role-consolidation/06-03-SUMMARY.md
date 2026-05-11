---
phase: 06-role-consolidation
plan: "03"
subsystem: tests
tags: [rbac, userrole, test-fixtures, pytest]

requires:
  - 06-01
provides:
  - All four test files using "admin" role strings (zero "compliance" role strings)
  - Fixture names: admin_user, seeded_admin_user
  - Helper names: _admin_token, _get_admin_token
  - Test function names updated to _requires_admin_role
  - Full test suite passing (85 passed, 2 skipped)
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - tests/test_05_01_audit_documents_api.py
    - tests/test_query.py
    - tests/test_ingestion.py
    - tests/test_vector_repo.py

key-decisions:
  - "seed_users.json compliance role string deferred — out of scope for Plan 06-03 (test files only)"

patterns-established: []

requirements-completed: [ROLE-01]

duration: 5min
completed: "2026-05-11"
---

# Phase 6 Plan 03: Role Consolidation — Test Updates Summary

**Four test files updated: all "compliance" role strings replaced with "admin"; fixture/helper/test names renamed; full suite passes (85 passed, 2 skipped)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-11T04:34:34Z
- **Completed:** 2026-05-11T04:39:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Renamed `_compliance_token` → `_admin_token` helper (role: admin, id: admin-user) in test_05_01_audit_documents_api.py
- Renamed `seeded_compliance_user` → `seeded_admin_user` fixture; updated all 5 call sites
- Renamed 3 test functions: `test_audit_list_requires_compliance_role`, `test_audit_detail_requires_compliance_role`, `test_documents_list_requires_compliance_role` → `*_requires_admin_role`
- Updated all `_compliance_token()` call sites → `_admin_token()` across audit/documents tests
- Updated single role assertion in test_query.py: `"compliance"` → `"admin"` in `test_query_rbac_enforcement`
- Renamed `compliance_user` fixture → `admin_user` in test_ingestion.py; updated all 9 call sites
- Renamed `_get_compliance_token` → `_get_admin_token` helper; updated all 9 call sites
- Renamed `test_ingest_requires_compliance_role` → `test_ingest_requires_admin_role`
- Updated `allowed_roles` assertion: `{"senior_adviser", "compliance"}` → `{"senior_adviser", "admin"}`
- Updated all 4 tier `allowed_roles` arrays in test_vector_repo.py fixture seed data
- Renamed `test_rbac_filter_compliance` → `test_rbac_filter_admin`
- Full test suite: 85 passed, 2 skipped, 0 failures

## Task Commits

1. **Task 1: Update test_05_01_audit_documents_api.py and test_query.py** — `08411b5` (feat)
2. **Task 2: Update test_ingestion.py and test_vector_repo.py, run full suite** — `5dc5473` (feat)

## Files Created/Modified

- `tests/test_05_01_audit_documents_api.py` — helper, fixture, 3 test functions renamed; all call sites updated
- `tests/test_query.py` — single role assertion updated
- `tests/test_ingestion.py` — fixture, helper, 1 test function renamed; all call sites + allowed_roles assertion updated
- `tests/test_vector_repo.py` — all 4 tier allowed_roles arrays updated; test function renamed

## Decisions Made

- `backend/seed_users.json` contains `"role": "compliance"` — deferred as out of scope for Plan 06-03 (plan covers test files only; seed_users.json is a data file not in files_modified)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Worktree venv was freshly created; required `uv pip install -e ".[dev]"` and copying `.env` from main repo before tests could run. Standard worktree setup, not a deviation.

## Deferred Items

| Item | File | Reason |
|------|------|--------|
| `"role": "compliance"` seed data | backend/seed_users.json | Out of scope — Plan 06-03 covers test files only; seed_users.json not in files_modified |

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

---
## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit 08411b5: FOUND
- Commit 5dc5473: FOUND

*Phase: 06-role-consolidation*
*Completed: 2026-05-11*
