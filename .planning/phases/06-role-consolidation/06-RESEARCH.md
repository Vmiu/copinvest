# Phase 6: Role Consolidation — Research

**Phase:** 6 — Role Consolidation
**Requirement:** ROLE-01
**Researched:** 2026-05-11

## Summary

This is a pure cross-cutting rename: `compliance` → `admin` across every layer. No new logic, no new endpoints. The risk surface is the PostgreSQL native enum type and the Qdrant `allowed_roles` payload strings stored in existing chunks.

---

## Validation Architecture

### What needs to change

| Layer | Location | Change |
|-------|----------|--------|
| Python enum | `backend/models/enums.py` | `compliance = "compliance"` → `admin = "admin"` |
| RBAC guards | `backend/routers/audit.py` (×3), `ingest.py`, `documents.py`, `query.py` | `"compliance"` → `"admin"` in `require_role(...)` calls |
| TIER_TO_ROLES | `backend/services/ingestion_service.py` | Replace `"compliance"` with `"admin"` in all 4 tier lists + fallback |
| DB enum type | Alembic migration | Add `admin`, UPDATE rows, remove `compliance` from `userrole` enum |
| Seed data | `backend/seed_users.json` | `"role": "compliance"` → `"role": "admin"`, update password hint |
| Frontend | `frontend/src/pages/LoginPage.tsx` | `COMPLIANCE_PASSWORD` constant rename + value |
| Tests | `tests/test_05_01_audit_documents_api.py`, `test_ingestion.py`, `test_vector_repo.py`, `test_query.py` | All `"compliance"` role strings, fixture names, helper names |
| Qdrant payloads | Existing chunks in vector store | `allowed_roles` arrays containing `"compliance"` → `"admin"` |

### DB migration strategy

PostgreSQL native enums cannot have values renamed in-place before PG 10 `ALTER TYPE ... RENAME VALUE`. Since the project targets SQLite (dev) + PostgreSQL (prod), the safest Alembic approach is:

1. Add `'admin'` to the `userrole` enum: `ALTER TYPE userrole ADD VALUE 'admin'`
2. `UPDATE users SET role = 'admin' WHERE role = 'compliance'`
3. Drop `'compliance'` from the enum — PostgreSQL requires recreating the type:
   - Create new type `userrole_new` with `('adviser', 'senior_adviser', 'admin')`
   - `ALTER TABLE users ALTER COLUMN role TYPE userrole_new USING role::text::userrole_new`
   - `DROP TYPE userrole`
   - `ALTER TYPE userrole_new RENAME TO userrole`

For SQLite (dev): SQLite stores enums as VARCHAR, so only the `UPDATE` statement is needed.

The migration must be conditional on dialect or use `op.execute()` with raw SQL guarded by `op.get_bind().dialect.name`.

### Qdrant payload update

Existing chunks have `allowed_roles` arrays like `["adviser", "senior_adviser", "compliance"]`. These must be updated via the Qdrant `set_payload` API (or `overwrite_payload`) on all points where `allowed_roles` contains `"compliance"`.

Pattern:
```python
# Scroll all points, filter those with "compliance" in allowed_roles, update payload
client.scroll(collection_name, with_payload=True, limit=100)
# For each matching point: replace "compliance" with "admin" in allowed_roles
client.overwrite_payload(collection_name, payload={"allowed_roles": updated_list}, points=[point_id])
```

This is a one-time migration script, not a service change. It should be a standalone `scripts/migrate_qdrant_roles.py`.

### Test update strategy

Tests use `"compliance"` in three ways:
1. **Role string in JWT payload** — change to `"admin"`
2. **Fixture/helper names** (`compliance_user`, `_compliance_token`, `seeded_compliance_user`) — rename for clarity, but the test logic is unchanged
3. **Test names** (`test_audit_list_requires_compliance_role`) — rename to `_requires_admin_role`
4. **`allowed_roles` assertions** in `test_ingestion.py:330` and `test_vector_repo.py` — update expected values

### What does NOT change

- `backend/services/generation_service.py:9` — "compliance-aware financial assistant" is a prose description in a system prompt, not a role reference. Leave it.
- `tests/test_ingestion.py:121` — `"Chunk 2 content about compliance"` is document content, not a role. Leave it.
- Any use of "compliance" as a domain concept (regulatory compliance) vs. the role name.

---

## Execution Order

1. **Alembic migration** (DB first — enum type must exist before Python code uses it)
2. **Python enum + backend code** (enum, routers, services)
3. **Qdrant migration script** (run after enum is updated so new ingestion uses `admin`)
4. **Seed data** (JSON file)
5. **Frontend** (LoginPage constant)
6. **Tests** (update all role strings and fixture names)

---

## RESEARCH COMPLETE
