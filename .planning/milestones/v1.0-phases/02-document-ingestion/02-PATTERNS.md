# Phase 2: Document Ingestion - Pattern Map

**Mapped:** 2026-05-01
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/models/document.py` | model | CRUD | `backend/models/audit_log.py` | exact |
| `backend/repositories/document_repo.py` | repository | CRUD | `backend/repositories/audit_repo.py` | exact |
| `backend/repositories/vector_repo.py` (modify) | repository | CRUD | `backend/repositories/vector_repo.py` | self |
| `backend/services/ingestion_service.py` | service | transform | `backend/services/audit_service.py` | role-match |
| `backend/services/chunking_service.py` | service | request-response | `backend/services/audit_service.py` | role-match |
| `backend/services/embedding_service.py` | service | batch | `backend/services/audit_service.py` | role-match |
| `backend/routers/ingest.py` | router | request-response | `backend/routers/auth.py` | exact |
| `backend/schemas/ingest.py` | schema | — | `backend/schemas/auth.py` | exact |
| `backend/core/config.py` (modify) | config | — | `backend/core/config.py` | self |
| `alembic/versions/xxx_add_document_registry.py` | migration | — | `alembic/versions/0f1eb48835fc_create_users_table.py` | exact |
| `tests/test_ingestion.py` | test | — | `tests/test_auth.py` | exact |

---

## Pattern Assignments

### `backend/models/document.py` (model, CRUD)

**Analog:** `backend/models/audit_log.py`

**Imports pattern** (lines 1-7):
```python
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
```

**Core model pattern** (lines 10-42):
```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # nullable optional fields:
    retrieved_chunks: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_tier_accessed: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Key notes for DocumentRecord:**
- Use `Mapped[str]` / `Mapped[int]` / `Mapped[str | None]` pattern throughout
- `ingested_by` is a ForeignKey to `users.id` (same pattern as `user_id` above)
- `warnings` is `Mapped[str | None] = mapped_column(Text, nullable=True)` — stored as JSON string
- `document_id` needs `unique=True, index=True` (same as `email` in `User` model)
- No `SAEnum` needed — `sensitivity_tier` is a plain `Integer`, not an enum column

---

### `backend/repositories/document_repo.py` (repository, CRUD)

**Analog:** `backend/repositories/audit_repo.py`

**Imports pattern** (lines 1-4):
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
```

**Core CRUD pattern** (lines 7-17):
```python
async def get_audit_by_id(db: AsyncSession, trace_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == trace_id))
    return result.scalar_one_or_none()

async def get_audits_by_session(db: AsyncSession, session_id: str) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    return list(result.scalars().all())
```

**Key notes for document_repo:**
- `upsert_document_record()` — use `select` to check if `document_id` exists, then update or `db.add()` new
- `get_document_by_id()` — same `scalar_one_or_none()` pattern
- All functions are `async def`, take `db: AsyncSession` as first arg
- Call `await db.flush()` after mutations (not `commit()` — let the router/caller commit)

---

### `backend/repositories/vector_repo.py` (modify — add upsert/delete)

**Analog:** self — extend existing file

**Existing imports** (lines 1-12):
```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    VectorParams,
)

from backend.core.config import get_settings
```

**Add to imports:** `PointStruct` from `qdrant_client.models`

**Existing setup_collection pattern** (lines 19-41) — add `source_id` payload index here:
```python
client.create_payload_index(
    collection_name=name,
    field_name="source_id",          # ADD THIS
    field_schema=PayloadSchemaType.KEYWORD,
)
```

**New upsert pattern to add** (from RESEARCH.md §4):
```python
from qdrant_client.models import PointStruct
import uuid

def upsert_chunks(
    client: QdrantClient,
    chunks: list[str],
    vectors: list[list[float]],
    payload_base: dict,
    collection: str | None = None,
) -> None:
    settings = get_settings()
    name = collection or settings.qdrant_collection
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={**payload_base, "chunk_index": i, "text": chunk},
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    client.upsert(collection_name=name, points=points)
```

**New delete pattern to add** (from RESEARCH.md §4):
```python
def delete_by_source(
    client: QdrantClient,
    document_id: str,
    collection: str | None = None,
) -> None:
    settings = get_settings()
    name = collection or settings.qdrant_collection
    client.delete(
        collection_name=name,
        points_selector=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=document_id))]
        ),
    )
```

**Key notes:** Both new functions follow the same `get_settings()` + `collection or settings.qdrant_collection` pattern as `query_with_rbac`. Keep them as module-level functions (not a class), consistent with existing style.

---

### `backend/services/ingestion_service.py` (service, transform)

**Analog:** `backend/services/session_service.py` (orchestration pattern) + `backend/services/audit_service.py` (async db writes)

**Imports pattern** (session_service.py lines 1-8):
```python
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import Session as AuditSession
```

**Async orchestration pattern** (session_service.py lines 12-36):
```python
async def get_or_create_session(db: AsyncSession, user_id: str) -> str:
    # ... query, mutate, db.add(), await db.flush(), return value
```

**Key notes for ingestion_service:**
- Single `async def ingest_document(...)` function that orchestrates: parse → chunk → embed → store → record
- Takes `db: AsyncSession`, `qdrant_client: QdrantClient`, and document params as arguments
- Calls `chunking_service`, `embedding_service`, `vector_repo`, `document_repo` in sequence
- Wraps docling call in `asyncio.to_thread()` (CPU-bound, synchronous)
- On `ConversionError`: raise `HTTPException(status_code=422, ...)`
- On LLM failure after retries: raise `HTTPException(status_code=422, ...)`
- Returns a dict/schema matching `IngestResponse`

---

### `backend/services/chunking_service.py` (service, request-response)

**Analog:** `backend/services/audit_service.py` (async function module pattern)

**Imports pattern** (audit_service.py lines 1-7):
```python
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.models.enums import AuditStatus, AdviserAction
```

**Key notes for chunking_service:**
- Module of async functions, no class
- `async def chunk_document(markdown: str, client: AsyncOpenAI) -> list[str]`
- Retry loop: `for attempt in range(3):` with `try/except` — raise on 3rd failure
- Post-process: `[c.strip() for c in raw.split("\n---\n") if c.strip()]`
- `temperature=0.0` for deterministic output
- Import `AsyncOpenAI` from `openai`; get `openai_api_key` from `get_settings()`

---

### `backend/services/embedding_service.py` (service, batch)

**Analog:** `backend/services/audit_service.py` (async function module pattern)

**Key notes:**
- Single `async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]`
- Calls `client.embeddings.create(model="text-embedding-3-small", input=chunks)`
- Returns `[item.embedding for item in response.data]`
- Same module-of-async-functions pattern as `audit_service.py`

---

### `backend/routers/ingest.py` (router, request-response)

**Analog:** `backend/routers/auth.py`

**Imports pattern** (auth.py lines 1-9):
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import verify_password, create_access_token
from backend.repositories.user_repo import get_user_by_email
from backend.schemas.auth import TokenResponse
```

**Router declaration pattern** (auth.py line 11):
```python
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
```

**Endpoint with dependency injection** (auth.py lines 14-27):
```python
@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    ...
```

**Key notes for ingest.py:**
- `router = APIRouter(prefix="/api/v1", tags=["ingest"])`
- Endpoint signature uses `UploadFile = File(...)`, `SensitivityTier = Form(...)`, `document_id: str | None = Form(None)`
- Auth dependency: `current_user: dict = Depends(get_current_user)` then check `current_user["role"] == "compliance"` — raise `HTTP_403_FORBIDDEN` if not
- `db: AsyncSession = Depends(get_db)` — same pattern as auth.py
- Save `UploadFile` to `tempfile.NamedTemporaryFile` before passing to docling
- Register router in `backend/main.py` with `app.include_router(ingest_router)`

---

### `backend/schemas/ingest.py` (schema)

**Analog:** `backend/schemas/auth.py`

**Pattern** (auth.py lines 1-5):
```python
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

**Key notes for ingest schemas:**
- `IngestResponse(BaseModel)` with fields: `document_id: str`, `chunk_count: int`, `char_count: int`, `warnings: list[str]`, `parse_duration_ms: int`
- Plain `BaseModel` subclasses, no `model_config` needed
- No `from __future__ import annotations` — not used in existing schemas

---

### `backend/core/config.py` (modify — add openai_api_key)

**Analog:** self

**Existing pattern** (config.py lines 6-15):
```python
class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./copinvest.db"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"
    secret_key: str  # No default -- forces explicit config
    access_token_expire_minutes: int = 1440  # 24h
    debug: bool = False

    model_config = {"env_file": ".env"}
```

**Add one field** — follow the `secret_key` pattern (no default, forces explicit config):
```python
openai_api_key: str  # No default -- forces explicit config
```

---

### `alembic/versions/xxx_add_document_registry.py` (migration)

**Analog:** `alembic/versions/0f1eb48835fc_create_users_table.py`

**Header pattern** (lines 1-17):
```python
"""add document registry table

Revision ID: <generated>
Revises: 0f1eb48835fc
Create Date: ...
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '<generated>'
down_revision: Union[str, Sequence[str], None] = '0f1eb48835fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**upgrade() pattern** (lines 22-62):
```python
def upgrade() -> None:
    op.create_table('document_registry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.String(255), nullable=False),
    sa.Column('filename', sa.String(500), nullable=False),
    ...
    sa.ForeignKeyConstraint(['ingested_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_registry_document_id'), 'document_registry', ['document_id'], unique=True)
```

**downgrade() pattern** (lines 65-74):
```python
def downgrade() -> None:
    op.drop_index(op.f('ix_document_registry_document_id'), table_name='document_registry')
    op.drop_table('document_registry')
```

---

### `tests/test_ingestion.py` (test)

**Analog:** `tests/test_auth.py` + `tests/conftest.py`

**Fixture pattern** (test_auth.py lines 11-21):
```python
@pytest_asyncio.fixture
async def seeded_user(db_session):
    user = User(id="test-user-1", email="alice@test.hk", ...)
    db_session.add(user)
    await db_session.commit()
    return user
```

**HTTP test pattern** (test_auth.py lines 24-31):
```python
async def test_login_success(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "alice@test.hk", "password": "password123"},
    )
    assert response.status_code == 200
```

**conftest.py dependency override pattern** (lines 22-29):
```python
async def override_get_db():
    yield db_session

app.dependency_overrides[get_db] = override_get_db
```

**Key notes for test_ingestion.py:**
- Use `unittest.mock.AsyncMock` / `patch` to mock `AsyncOpenAI` (chunking + embedding calls)
- Use Qdrant in-memory mode: `QdrantClient(":memory:")` — override the qdrant client dependency
- File upload via httpx: `files={"file": ("test.pdf", b"...", "application/pdf")}` + `data={"sensitivity_tier": "1"}`
- Auth header: login first (same pattern as `test_protected_endpoint_valid_token`), then pass `Authorization: Bearer <token>`
- Test 403 by using a non-compliance role user (role="adviser")
- Test 422 by mocking docling to raise `ConversionError`

---

## Shared Patterns

### Authentication / Role Check
**Source:** `backend/core/dependencies.py` + `backend/routers/auth.py`
**Apply to:** `backend/routers/ingest.py`
```python
# In ingest.py endpoint signature:
current_user: dict = Depends(get_current_user)

# Role enforcement inside handler (no separate require_role() needed — inline check):
if current_user["role"] != "compliance":
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compliance role required")
```

### Async DB Session
**Source:** `backend/core/database.py` via `get_db()`
**Apply to:** `backend/routers/ingest.py`, `backend/repositories/document_repo.py`
```python
db: AsyncSession = Depends(get_db)
# In repositories: await db.flush() after mutations, not db.commit()
# Commit happens at the router level or via FastAPI's request lifecycle
```

### Settings Access
**Source:** `backend/core/config.py`
**Apply to:** `backend/services/chunking_service.py`, `backend/services/embedding_service.py`, `backend/repositories/vector_repo.py`
```python
from backend.core.config import get_settings

settings = get_settings()  # lru_cache — safe to call at function scope
```

### Module-of-Functions Service Pattern
**Source:** `backend/services/audit_service.py`, `backend/services/session_service.py`
**Apply to:** All new service files
- No classes. Module-level `async def` functions.
- Each function takes explicit dependencies as arguments (db session, client, etc.)
- No global state inside service modules.

### Structlog Logging
**Source:** `backend/main.py` lines 11-12
**Apply to:** `backend/services/ingestion_service.py`
```python
import structlog
logger = structlog.get_logger()
# Usage: logger.info("ingestion_started", document_id=document_id, filename=filename)
```

---

## No Analog Found

All files have close analogs in the existing codebase. No entries.

---

## Metadata

**Analog search scope:** `backend/` (all subdirectories), `alembic/versions/`, `tests/`
**Files scanned:** 15
**Pattern extraction date:** 2026-05-01
