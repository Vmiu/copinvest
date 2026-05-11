# Phase 6: Role Consolidation — Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 14
**Analogs found:** 14 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/models/enums.py` | model | — | self (modify in place) | exact |
| `backend/routers/audit.py` | router | request-response | self (modify in place) | exact |
| `backend/routers/ingest.py` | router | request-response | self (modify in place) | exact |
| `backend/routers/documents.py` | router | request-response | self (modify in place) | exact |
| `backend/routers/query.py` | router | request-response | self (modify in place) | exact |
| `backend/services/ingestion_service.py` | service | CRUD | self (modify in place) | exact |
| `alembic/versions/<rev>_rename_compliance_to_admin.py` | migration | batch | `alembic/versions/0f1eb48835fc_create_users_table.py` | role-match |
| `backend/seed_users.json` | config | — | self (modify in place) | exact |
| `frontend/src/pages/LoginPage.tsx` | component | request-response | self (modify in place) | exact |
| `tests/test_05_01_audit_documents_api.py` | test | request-response | self (modify in place) | exact |
| `tests/test_ingestion.py` | test | request-response | self (modify in place) | exact |
| `tests/test_vector_repo.py` | test | — | self (modify in place) | exact |
| `tests/test_query.py` | test | request-response | self (modify in place) | exact |
| `scripts/migrate_qdrant_roles.py` | utility | batch | `backend/services/ingestion_service.py` (Qdrant client usage) | partial |

---

## Pattern Assignments

### `backend/models/enums.py` (model)

**Change:** Single line — rename enum member.

**Current pattern** (lines 4–7):
```python
class UserRole(str, enum.Enum):
    adviser = "adviser"
    senior_adviser = "senior_adviser"
    compliance = "compliance"
```

**Target pattern:**
```python
class UserRole(str, enum.Enum):
    adviser = "adviser"
    senior_adviser = "senior_adviser"
    admin = "admin"
```

---

### `backend/routers/audit.py` (router, request-response)

**Change:** Replace `"compliance"` with `"admin"` in all three `require_role(...)` calls.

**Current pattern** (lines 19, 35, 55):
```python
current_user: dict = Depends(require_role("compliance")),
```

**Target pattern:**
```python
current_user: dict = Depends(require_role("admin")),
```

---

### `backend/routers/ingest.py` (router, request-response)

**Change:** Replace `"compliance"` with `"admin"` in `require_role(...)` call.

**Current pattern** (line 25):
```python
current_user: dict = Depends(require_role("compliance")),
```

**Target pattern:**
```python
current_user: dict = Depends(require_role("admin")),
```

---

### `backend/routers/documents.py` (router, request-response)

**Change:** Replace `"compliance"` with `"admin"` in `require_role(...)` call.

**Current pattern** (line 17):
```python
current_user: dict = Depends(require_role("compliance")),
```

**Target pattern:**
```python
current_user: dict = Depends(require_role("admin")),
```

---

### `backend/routers/query.py` (router, request-response)

**Change:** Replace `"compliance"` with `"admin"` in `require_role(...)` call.

**Current pattern** (line 25):
```python
current_user: dict = Depends(require_role("adviser", "senior_adviser", "compliance")),
```

**Target pattern:**
```python
current_user: dict = Depends(require_role("adviser", "senior_adviser", "admin")),
```

---

### `backend/services/ingestion_service.py` (service, CRUD)

**Change:** Replace `"compliance"` with `"admin"` in `TIER_TO_ROLES` dict and fallback.

**Current pattern** (lines 20–25, 83):
```python
TIER_TO_ROLES: dict[int, list[str]] = {
    SensitivityTier.public: ["adviser", "senior_adviser", "compliance"],
    SensitivityTier.internal: ["senior_adviser", "compliance"],
    SensitivityTier.restricted: ["senior_adviser", "compliance"],
    SensitivityTier.confidential: ["compliance"],
}
# ...
allowed_roles = TIER_TO_ROLES.get(sensitivity_tier.value, ["compliance"])
```

**Target pattern:**
```python
TIER_TO_ROLES: dict[int, list[str]] = {
    SensitivityTier.public: ["adviser", "senior_adviser", "admin"],
    SensitivityTier.internal: ["senior_adviser", "admin"],
    SensitivityTier.restricted: ["senior_adviser", "admin"],
    SensitivityTier.confidential: ["admin"],
}
# ...
allowed_roles = TIER_TO_ROLES.get(sensitivity_tier.value, ["admin"])
```

---

### `alembic/versions/<rev>_rename_compliance_to_admin.py` (migration, batch)

**Analog:** `alembic/versions/0f1eb48835fc_create_users_table.py`

**Migration file structure** (lines 1–17 of analog):
```python
"""rename compliance to admin in userrole enum

Revision ID: <new_rev>
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11 ...

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '<new_rev>'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Dialect-conditional upgrade pattern** (copy from research strategy):
```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Step 1: add new value
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'")
        # Step 2: migrate data
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'compliance'")
        # Step 3: recreate enum without 'compliance'
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR")
        op.execute("DROP TYPE userrole")
        op.execute("CREATE TYPE userrole AS ENUM ('adviser', 'senior_adviser', 'admin')")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
    else:
        # SQLite: enum stored as VARCHAR, only data migration needed
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'compliance'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR")
        op.execute("DROP TYPE userrole")
        op.execute("CREATE TYPE userrole AS ENUM ('adviser', 'senior_adviser', 'compliance')")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
        op.execute("UPDATE users SET role = 'compliance' WHERE role = 'admin'")
    else:
        op.execute("UPDATE users SET role = 'compliance' WHERE role = 'admin'")
```

---

### `backend/seed_users.json` (config)

**Change:** Update carol's role and password.

**Current pattern** (line 4):
```json
{"id": "user-003", "email": "carol@copinvest.hk", "password": "compliance123", "role": "compliance"}
```

**Target pattern:**
```json
{"id": "user-003", "email": "carol@copinvest.hk", "password": "admin123", "role": "admin"}
```

---

### `frontend/src/pages/LoginPage.tsx` (component, request-response)

**Change:** Rename constants and update values.

**Current pattern** (lines 5–6, 20):
```typescript
const COMPLIANCE_EMAIL = "carol@copinvest.hk";
const COMPLIANCE_PASSWORD = "compliance123";
// ...
if (email !== COMPLIANCE_EMAIL || password !== COMPLIANCE_PASSWORD) {
```

**Target pattern:**
```typescript
const ADMIN_EMAIL = "carol@copinvest.hk";
const ADMIN_PASSWORD = "admin123";
// ...
if (email !== ADMIN_EMAIL || password !== ADMIN_PASSWORD) {
```

---

### `tests/test_05_01_audit_documents_api.py` (test, request-response)

**Change:** Rename helper, fixture, and update role strings. Three locations.

**Current pattern** (lines 14–15, 23–29, 92–93, 178–179, 193–194):
```python
def _compliance_token(user_id: str = "compliance-user") -> str:
    return create_access_token({"sub": user_id, "role": "compliance"})

async def seeded_compliance_user(db_session):
    user = User(id="compliance-user", email="compliance@test.hk",
                hashed_password=hash_password("pw"), role="compliance")

# test names:
async def test_audit_list_requires_compliance_role(...)
async def test_audit_detail_requires_compliance_role(...)
async def test_documents_list_requires_compliance_role(...)
```

**Target pattern:**
```python
def _admin_token(user_id: str = "admin-user") -> str:
    return create_access_token({"sub": user_id, "role": "admin"})

async def seeded_admin_user(db_session):
    user = User(id="admin-user", email="admin@test.hk",
                hashed_password=hash_password("pw"), role="admin")

# test names:
async def test_audit_list_requires_admin_role(...)
async def test_audit_detail_requires_admin_role(...)
async def test_documents_list_requires_admin_role(...)
```

Note: All call sites that pass `seeded_compliance_user` as a fixture arg or call `_compliance_token()` must be updated to `seeded_admin_user` / `_admin_token()`.

---

### `tests/test_ingestion.py` (test, request-response)

**Change:** Rename fixture, helper, and update role strings + `allowed_roles` assertion.

**Current pattern** (lines 38–48, 100–107, 267–268, 330):
```python
async def compliance_user(db_session_ingest):
    user = User(id="compliance-user-1", email="compliance@test.hk",
                hashed_password=hash_password("compliancepass"), role="compliance")

async def _get_compliance_token(client) -> str:
    resp = await client.post("/api/v1/auth/token",
        data={"username": "compliance@test.hk", "password": "compliancepass"})

async def test_ingest_requires_compliance_role(...)  # line 267

# line 330 — allowed_roles assertion:
assert set(pt.payload["allowed_roles"]) == {"senior_adviser", "compliance"}
```

**Target pattern:**
```python
async def admin_user(db_session_ingest):
    user = User(id="admin-user-1", email="admin@test.hk",
                hashed_password=hash_password("adminpass"), role="admin")

async def _get_admin_token(client) -> str:
    resp = await client.post("/api/v1/auth/token",
        data={"username": "admin@test.hk", "password": "adminpass"})

async def test_ingest_requires_admin_role(...)

# line 330 — allowed_roles assertion:
assert set(pt.payload["allowed_roles"]) == {"senior_adviser", "admin"}
```

Note: `_MOCK_CHUNKS` line 121 (`"Chunk 2 content about compliance"`) is document content — do NOT change it.

---

### `tests/test_vector_repo.py` (test)

**Change:** Replace `"compliance"` with `"admin"` in all `allowed_roles` payload arrays in fixture seed data.

**Current pattern** (lines 44–75, 88–109):
```python
"allowed_roles": ["adviser", "senior_adviser", "compliance"],  # tier 1
"allowed_roles": ["senior_adviser", "compliance"],             # tier 2
"allowed_roles": ["senior_adviser", "compliance"],             # tier 3
"allowed_roles": ["compliance"],                               # tier 4
```

**Target pattern:**
```python
"allowed_roles": ["adviser", "senior_adviser", "admin"],  # tier 1
"allowed_roles": ["senior_adviser", "admin"],             # tier 2
"allowed_roles": ["senior_adviser", "admin"],             # tier 3
"allowed_roles": ["admin"],                               # tier 4
```

Also update the docstring comment at line 32–35:
```python
# tier 1 (public): adviser, senior_adviser, admin
# tier 2 (internal): senior_adviser, admin
# tier 3 (restricted): senior_adviser, admin
# tier 4 (confidential): admin only
```

---

### `tests/test_query.py` (test, request-response)

**Change:** Single assertion update.

**Current pattern** (line 186):
```python
assert captured_role["role"] in ("adviser", "senior_adviser", "compliance")
```

**Target pattern:**
```python
assert captured_role["role"] in ("adviser", "senior_adviser", "admin")
```

---

### `scripts/migrate_qdrant_roles.py` (utility, batch)

**No analog exists** — new script. Use Qdrant client scroll+overwrite pattern from `backend/services/ingestion_service.py` (lines 1–17 for imports, lines 83–90 for Qdrant client usage).

**Qdrant client import pattern** (from `ingestion_service.py` lines 8–9):
```python
from qdrant_client import QdrantClient
```

**Qdrant scroll + overwrite pattern** (research-derived, no existing analog):
```python
from qdrant_client import QdrantClient

def migrate(collection: str, qdrant_url: str) -> None:
    client = QdrantClient(url=qdrant_url)
    offset = None
    updated = 0
    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            with_payload=True,
            limit=100,
            offset=offset,
        )
        for point in results:
            roles = point.payload.get("allowed_roles", [])
            if "compliance" in roles:
                new_roles = ["admin" if r == "compliance" else r for r in roles]
                client.overwrite_payload(
                    collection_name=collection,
                    payload={"allowed_roles": new_roles},
                    points=[point.id],
                )
                updated += 1
        if next_offset is None:
            break
        offset = next_offset
    print(f"Updated {updated} points in '{collection}'")
```

---

## Shared Patterns

### `require_role(...)` guard
**Source:** `backend/core/dependencies.py` (called in all routers)
**Apply to:** `audit.py` (×3), `ingest.py`, `documents.py`, `query.py`
**Pattern:** Pass role string(s) as positional args — `require_role("admin")` or `require_role("adviser", "senior_adviser", "admin")`. No other change to the function signature or surrounding code.

### Dialect-conditional Alembic SQL
**Source:** `alembic/versions/0f1eb48835fc_create_users_table.py` (structure)
**Apply to:** new migration file
**Pattern:** Use `op.get_bind().dialect.name == "postgresql"` guard. SQLite branch only needs `UPDATE`. PostgreSQL branch must drop and recreate the native enum type.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `scripts/migrate_qdrant_roles.py` | utility | batch | No existing one-shot migration scripts in codebase |

---

## Metadata

**Analog search scope:** `backend/`, `alembic/versions/`, `tests/`, `frontend/src/`
**Files scanned:** 13 existing files read
**Pattern extraction date:** 2026-05-11
