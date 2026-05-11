---
phase: 06-role-consolidation
reviewed: 2026-05-11T04:43:29Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - alembic/versions/b9c4d2e1f3a7_rename_compliance_to_admin.py
  - backend/models/enums.py
  - backend/routers/audit.py
  - backend/routers/ingest.py
  - backend/routers/documents.py
  - backend/routers/query.py
  - backend/services/ingestion_service.py
  - scripts/migrate_qdrant_roles.py
  - backend/seed_users.json
  - frontend/src/pages/LoginPage.tsx
  - tests/test_05_01_audit_documents_api.py
  - tests/test_ingestion.py
  - tests/test_vector_repo.py
  - tests/test_query.py
findings:
  critical: 2
  warning: 1
  info: 0
  total: 3
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-05-11T04:43:29Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Role rename from `compliance` → `admin` is mechanically correct across the DB migration, Qdrant migration script, enum, and all routers. The RBAC enforcement chain (`require_role` → JWT → Qdrant pre-filter) is sound. Two security issues exist in the frontend and seed file: hardcoded admin credentials shipped in the JS bundle, and plaintext passwords committed to source.

## Critical Issues

### CR-01: Admin password hardcoded in frontend bundle

**File:** `frontend/src/pages/LoginPage.tsx:5-6`
**Issue:** `ADMIN_EMAIL` and `ADMIN_PASSWORD` are module-level constants compiled into the shipped JS bundle. Any user who opens DevTools or inspects the minified bundle can read `admin123`. The client-side credential check on line 20 is also security theatre — it can be bypassed entirely by calling `POST /api/v1/auth/token` directly. The real harm is credential exposure in the bundle.
**Fix:** Remove the constants and the client-side pre-check entirely. The form should submit directly to the API; the server is the only authority.

```tsx
// Remove lines 5-6 entirely:
// const ADMIN_EMAIL = "carol@copinvest.hk";
// const ADMIN_PASSWORD = "admin123";

// Replace handleSubmit — remove the early-return guard, go straight to fetch:
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  setLoading(true);
  setError("");
  try {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch("/api/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!res.ok) throw new Error();
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    onLogin(data.access_token);
  } catch {
    setError("Invalid credentials.");
  } finally {
    setLoading(false);
  }
}
```

### CR-02: Plaintext passwords committed to source

**File:** `backend/seed_users.json:2-4`
**Issue:** `adviser123`, `senior123`, and `admin123` are stored in plaintext in a committed file. If the seed script reads this file and inserts rows directly, passwords bypass hashing. Even if the seed script hashes them at load time, committing real-looking credentials to the repo means they appear in git history permanently and will be flagged by secret scanners.
**Fix:** Either (a) store only hashed values in the file (pre-hash with `hash_password()` and commit the bcrypt digests), or (b) remove passwords from the file and have the seed script generate random passwords printed once to stdout, never committed.

```json
[
  {"id": "user-001", "email": "alice@copinvest.hk", "hashed_password": "$2b$12$<bcrypt-hash>", "role": "adviser"},
  {"id": "user-002", "email": "bob@copinvest.hk",   "hashed_password": "$2b$12$<bcrypt-hash>", "role": "senior_adviser"},
  {"id": "user-003", "email": "carol@copinvest.hk", "hashed_password": "$2b$12$<bcrypt-hash>", "role": "admin"}
]
```

## Warnings

### WR-01: Alembic downgrade silently relabels post-rename admin users as compliance

**File:** `alembic/versions/b9c4d2e1f3a7_rename_compliance_to_admin.py:36-39`
**Issue:** The downgrade runs `UPDATE users SET role = 'compliance' WHERE role = 'admin'`. Any user created as `admin` after the rename (who was never `compliance`) will be relabeled `compliance` on rollback. There is no way to distinguish original-compliance users from new-admin users, so a rollback is destructive.
**Fix:** Document this limitation explicitly in the migration docstring so operators know a downgrade is not safely reversible. If rollback safety matters, add a `migrated_from_compliance` boolean column before the rename to track provenance.

```python
"""rename compliance to admin in userrole enum

Revision ID: b9c4d2e1f3a7
...

WARNING: downgrade() is NOT safely reversible. Any user created as 'admin'
after this migration was applied will be relabeled 'compliance' on rollback,
regardless of whether they were originally a compliance user.
"""
```

---

_Reviewed: 2026-05-11T04:43:29Z_
_Reviewer: Kiro (gsd-code-reviewer)_
_Depth: standard_
