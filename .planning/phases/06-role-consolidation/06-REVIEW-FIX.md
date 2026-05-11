---
phase: 06-role-consolidation
fixed_at: 2026-05-11T05:01:00Z
review_path: .planning/phases/06-role-consolidation/06-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-05-11T05:01:00Z
**Source review:** .planning/phases/06-role-consolidation/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Admin password hardcoded in frontend bundle

**Files modified:** `frontend/src/pages/LoginPage.tsx`
**Commit:** c1cb5a9
**Applied fix:** Removed `ADMIN_EMAIL` and `ADMIN_PASSWORD` module-level constants (lines 5-6). Removed the client-side credential pre-check early-return guard from `handleSubmit`. The form now submits directly to the API; error message unified to "Invalid credentials."

### CR-02: Plaintext passwords committed to source

**Files modified:** `backend/seed_users.json`, `backend/scripts/seed_users.py`
**Commit:** f5d03bc
**Applied fix:** Replaced `password` field with `hashed_password` containing pre-computed bcrypt digests in `seed_users.json`. Updated `seed_users.py` to read `u["hashed_password"]` directly and removed the `hash_password` import and call — no double-hashing.

### WR-01: Alembic downgrade silently relabels post-rename admin users as compliance

**Files modified:** `alembic/versions/b9c4d2e1f3a7_rename_compliance_to_admin.py`
**Commit:** 17e5d80
**Applied fix:** Added WARNING paragraph to the migration module docstring documenting that `downgrade()` is not safely reversible and that any user created as `admin` after the migration will be relabeled `compliance` on rollback.

---

_Fixed: 2026-05-11T05:01:00Z_
_Fixer: Kiro (gsd-code-fixer)_
_Iteration: 1_
