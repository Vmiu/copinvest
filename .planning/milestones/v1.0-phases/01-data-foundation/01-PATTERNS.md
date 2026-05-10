# Phase 1: Data Foundation - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 28 (new files)
**Analogs found:** 0 / 28 (greenfield project)

## Greenfield Note

This is a greenfield project with no existing source code. All patterns below are derived from RESEARCH.md code examples, locked decisions in CONTEXT.md, and library documentation. Each file section includes the canonical code excerpt that the planner should use as the implementation template.

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `backend/main.py` | config | request-response | none (greenfield) | -- |
| `backend/core/config.py` | config | -- | none (greenfield) | -- |
| `backend/core/database.py` | config | CRUD | none (greenfield) | -- |
| `backend/core/security.py` | utility | request-response | none (greenfield) | -- |
| `backend/core/dependencies.py` | middleware | request-response | none (greenfield) | -- |
| `backend/routers/auth.py` | controller | request-response | none (greenfield) | -- |
| `backend/routers/query.py` | controller | request-response | none (greenfield) | -- |
| `backend/services/audit_service.py` | service | CRUD | none (greenfield) | -- |
| `backend/services/session_service.py` | service | CRUD | none (greenfield) | -- |
| `backend/repositories/user_repo.py` | repository | CRUD | none (greenfield) | -- |
| `backend/repositories/audit_repo.py` | repository | CRUD | none (greenfield) | -- |
| `backend/repositories/vector_repo.py` | repository | CRUD | none (greenfield) | -- |
| `backend/models/base.py` | model | -- | none (greenfield) | -- |
| `backend/models/user.py` | model | -- | none (greenfield) | -- |
| `backend/models/audit_log.py` | model | -- | none (greenfield) | -- |
| `backend/models/enums.py` | model | -- | none (greenfield) | -- |
| `backend/schemas/auth.py` | model | -- | none (greenfield) | -- |
| `backend/schemas/audit.py` | model | -- | none (greenfield) | -- |
| `backend/scripts/seed_users.py` | utility | file-I/O | none (greenfield) | -- |
| `backend/alembic/env.py` | config | -- | none (greenfield) | -- |
| `backend/alembic.ini` | config | -- | none (greenfield) | -- |
| `docker-compose.yml` | config | -- | none (greenfield) | -- |
| `backend/seed_users.json` | config | -- | none (greenfield) | -- |
| `pyproject.toml` | config | -- | none (greenfield) | -- |
| `tests/conftest.py` | test | -- | none (greenfield) | -- |
| `tests/test_auth.py` | test | request-response | none (greenfield) | -- |
| `tests/test_security.py` | test | request-response | none (greenfield) | -- |
| `tests/test_vector_repo.py` | test | CRUD | none (greenfield) | -- |
| `tests/test_audit.py` | test | CRUD | none (greenfield) | -- |
| `tests/test_session.py` | test | CRUD | none (greenfield) | -- |

## Pattern Assignments

### `backend/core/config.py` (config)

**Source:** RESEARCH.md + pydantic-settings docs

**Pattern: pydantic-settings BaseSettings with .env loading**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./copinvest.db"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    secret_key: str  # JWT signing key -- no default, must be set
    access_token_expire_minutes: int = 1440  # 24h
    debug: bool = False

    model_config = {"env_file": ".env"}

settings = Settings()
```

**Key decisions:**
- D-01: SQLite connection string uses `sqlite+aiosqlite:///` prefix (Pitfall 2)
- D-07: JWT expiry as config value (Discretion item)
- Secret key has no default -- forces explicit configuration

---

### `backend/core/database.py` (config, CRUD)

**Source:** RESEARCH.md lines 323-338

**Pattern: Async SQLAlchemy engine + sessionmaker**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

**Key decisions:**
- D-01: `sqlite+aiosqlite:///` for dev, SQLAlchemy abstracts dialect
- Pitfall 2: Must use aiosqlite driver for async SQLite
- `expire_on_commit=False` prevents lazy-load issues in async context

---

### `backend/core/security.py` (utility, request-response)

**Source:** RESEARCH.md lines 186-206 (JWT) + lines 342-354 (password)

**Pattern: JWT encode/decode with PyJWT + password hashing with pwdlib**
```python
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from core.config import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
```

**Key decisions:**
- Pitfall 1: pwdlib replaces passlib (broken on Python 3.13)
- D-07: JWT payload includes `sub` (user_id) and `role`
- Pitfall 5: Secret key must be 256-bit random

---

### `backend/core/dependencies.py` (middleware, request-response)

**Source:** RESEARCH.md lines 186-206

**Pattern: FastAPI OAuth2PasswordBearer + get_current_user dependency**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": user_id, "role": role}
```

**Key decisions:**
- D-07: Role extracted from JWT -- no DB lookup per request
- `tokenUrl` matches the auth router path

---

### `backend/models/enums.py` (model)

**Source:** CONTEXT.md D-04, D-05, D-08

**Pattern: Python enums for roles, tiers, actions, audit status**
```python
import enum

class UserRole(str, enum.Enum):
    adviser = "adviser"
    senior_adviser = "senior_adviser"
    compliance = "compliance"

class SensitivityTier(int, enum.Enum):
    public = 1
    internal = 2
    restricted = 3
    confidential = 4

class AdviserAction(str, enum.Enum):
    approved = "approved"
    edited = "edited"
    discarded = "discarded"

class AuditStatus(str, enum.Enum):
    received = "received"
    retrieved = "retrieved"
    generated = "generated"
    completed = "completed"
```

**Key decisions:**
- D-04: Three fixed roles
- D-05: Four sensitivity tiers with strict hierarchy
- Pitfall 6: AuditStatus tracks progressive record lifecycle

---

### `backend/models/base.py` (model)

**Source:** RESEARCH.md State of the Art table

**Pattern: SQLAlchemy 2.0 DeclarativeBase**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**Key decisions:**
- Uses new `DeclarativeBase` class style (not deprecated `declarative_base()` function)

---

### `backend/models/user.py` (model)

**Source:** CONTEXT.md D-04, D-06, D-07

**Pattern: User model with role enum**
```python
from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
from models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
```

**Key decisions:**
- D-06: Users seeded from config file, no registration
- D-07: Role stored on user, included in JWT at login

---

### `backend/models/audit_log.py` (model)

**Source:** CONTEXT.md D-08, D-09, D-10 + RESEARCH.md Pitfall 6

**Pattern: AuditLog with progressive update fields + Session model**
```python
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
from models.enums import AdviserAction, AuditStatus

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # trace_id
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String)  # "web" or "telegram"
    query_text: Mapped[str] = mapped_column(Text)
    status: Mapped[AuditStatus] = mapped_column(SAEnum(AuditStatus))
    # Updated after retrieval
    retrieved_chunks: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_tier_accessed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_sent: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Updated after LLM response
    llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Updated after adviser action
    adviser_action: Mapped[AdviserAction | None] = mapped_column(SAEnum(AdviserAction), nullable=True)
    adviser_edited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Key decisions:**
- D-08: Progressive lifecycle -- fields nullable until their pipeline stage
- D-09: Session model with 30-min inactivity timeout
- D-10: `sensitivity_tier_accessed` = max tier of retrieved chunks
- Pitfall 6: `status` enum tracks how far the pipeline got

---

### `backend/routers/auth.py` (controller, request-response)

**Source:** RESEARCH.md Pattern 1

**Pattern: FastAPI router with OAuth2 password flow**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import verify_password, create_access_token
from repositories.user_repo import get_user_by_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}
```

**Key decisions:**
- D-07: Role included in JWT payload
- Uses `OAuth2PasswordRequestForm` for Swagger UI integration
- `form.username` is the email field (OAuth2 spec uses "username")

---

### `backend/repositories/vector_repo.py` (repository, CRUD)

**Source:** RESEARCH.md lines 358-381 (Qdrant setup) + lines 214-232 (RBAC query)

**Pattern: Qdrant collection setup with payload indexes + RBAC-filtered query**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType, Filter, FieldCondition, MatchValue

def setup_collection(client: QdrantClient, collection_name: str = "documents"):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="allowed_roles",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="sensitivity_tier",
        field_schema=PayloadSchemaType.INTEGER,
    )

def query_with_rbac(client: QdrantClient, query_vector: list[float],
                    user_role: str, collection: str, limit: int = 20):
    return client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="allowed_roles", match=MatchValue(value=user_role))]
        ),
        limit=limit,
    )
```

**Key decisions:**
- D-02: Qdrant via Docker, qdrant-client SDK
- D-05: Pre-filtering by `allowed_roles` (not post-retrieval)
- Pitfall 4: Explicit payload indexes on `allowed_roles` and `sensitivity_tier`
- Discretion: 1536 dimensions for text-embedding-3-small, cosine distance

---

### `backend/services/audit_service.py` (service, CRUD)

**Source:** RESEARCH.md Pattern 3 (lines 236-256)

**Pattern: Progressive audit record create/update**
```python
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from models.audit_log import AuditLog
from models.enums import AuditStatus

async def create_audit_record(db: AsyncSession, user_id: str, query_text: str,
                               session_id: str, channel: str) -> AuditLog:
    audit = AuditLog(
        id=str(uuid4()), user_id=user_id, query_text=query_text,
        session_id=session_id, channel=channel,
        timestamp=datetime.now(timezone.utc), status=AuditStatus.received,
    )
    db.add(audit)
    await db.commit()
    return audit

async def update_retrieval(db: AsyncSession, audit: AuditLog,
                           chunks_json: str, max_tier: int, prompt: str):
    audit.retrieved_chunks = chunks_json
    audit.sensitivity_tier_accessed = max_tier
    audit.prompt_sent = prompt
    audit.status = AuditStatus.retrieved
    await db.commit()
```

**Key decisions:**
- D-08: Progressive lifecycle -- each stage commits independently
- D-10: `sensitivity_tier_accessed` set to max tier of retrieved chunks
- Pitfall 6: `status` field tracks pipeline progress for crash recovery

---

### `backend/services/session_service.py` (service, CRUD)

**Source:** CONTEXT.md D-09

**Pattern: Session creation with 30-min inactivity timeout**
```python
from datetime import datetime, timezone, timedelta

SESSION_TIMEOUT = timedelta(minutes=30)

async def get_or_create_session(db: AsyncSession, user_id: str) -> str:
    # Find active session for user (last activity < 30 min ago)
    # If found, return session_id
    # If not found or expired, create new session, return session_id
    ...
```

**Key decisions:**
- D-09: 30-minute inactivity timeout
- Session has start_time and end_time (end_time set when session expires)

---

### `backend/repositories/user_repo.py` (repository, CRUD)

**Pattern: Async SQLAlchemy select query**
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
```

**Key decisions:**
- Uses SQLAlchemy 2.0 `select()` style (not legacy `query()`)
- Returns `None` for missing users (caller handles 401)

---

### `backend/repositories/audit_repo.py` (repository, CRUD)

**Pattern: Same async select pattern as user_repo**
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.audit_log import AuditLog

async def get_audit_by_id(db: AsyncSession, trace_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == trace_id))
    return result.scalar_one_or_none()
```

---

### `backend/schemas/auth.py` (model)

**Pattern: Pydantic v2 response schemas**
```python
from pydantic import BaseModel

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

---

### `backend/schemas/audit.py` (model)

**Pattern: Pydantic v2 schemas with optional progressive fields**
```python
from pydantic import BaseModel
from datetime import datetime
from models.enums import AuditStatus, AdviserAction

class AuditRecordOut(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    query_text: str
    status: AuditStatus
    sensitivity_tier_accessed: int | None = None
    model_used: str | None = None
    adviser_action: AdviserAction | None = None

    model_config = {"from_attributes": True}
```

---

### `backend/main.py` (config, request-response)

**Pattern: FastAPI app factory with async lifespan**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.database import engine
from models.base import Base
from routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (dev only), init Qdrant collection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: dispose engine
    await engine.dispose()

app = FastAPI(title="CopInvest", lifespan=lifespan)
app.include_router(auth.router)
```

---

### `backend/scripts/seed_users.py` (utility, file-I/O)

**Source:** CONTEXT.md D-06

**Pattern: CLI script reading JSON seed file**
```python
import json
import asyncio
from core.database import async_session
from core.security import hash_password
from models.user import User

async def seed():
    with open("seed_users.json") as f:
        users = json.load(f)
    async with async_session() as db:
        for u in users:
            db.add(User(id=u["id"], email=u["email"],
                        hashed_password=hash_password(u["password"]),
                        role=u["role"]))
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed())
```

**Key decisions:**
- D-06: JSON seed file with email, password (plaintext in file, hashed on insert), role
- Discretion: JSON chosen over YAML (no extra dependency)

---

### `docker-compose.yml` (config)

**Source:** RESEARCH.md lines 384-397

**Pattern: Qdrant Docker service**
```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.17.1
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
```

**Key decisions:**
- D-02, D-03: Qdrant as Docker container for local dev

---

### `backend/alembic/env.py` (config)

**Source:** RESEARCH.md Pitfall 3

**Pattern: Async Alembic env.py**
- Must be initialized with `alembic init -t async alembic`
- Pitfall 3: Default sync template will fail with async engine
- `target_metadata = Base.metadata` must import from `models.base`

---

### `tests/conftest.py` (test)

**Pattern: Async test fixtures with in-memory SQLite**
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models.base import Base
from main import app
from core.database import get_db

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

**Key decisions:**
- In-memory SQLite for test isolation
- Dependency override pattern for injecting test DB
- httpx AsyncClient as test client (RESEARCH.md dev stack)

---

### Test files pattern (test_auth.py, test_security.py, test_vector_repo.py, test_audit.py, test_session.py)

**Pattern: pytest-asyncio test functions**
```python
import pytest

@pytest.mark.asyncio
async def test_example(client, db_session):
    response = await client.post("/api/v1/auth/token", data={...})
    assert response.status_code == 200
```

**Key decisions:**
- `@pytest.mark.asyncio` decorator on all async tests
- Fixtures from conftest.py (client, db_session)
- Test file maps to requirement IDs (see RESEARCH.md Validation Architecture)

## Shared Patterns

### Authentication Guard
**Apply to:** All controller/router files except `routers/auth.py`
```python
from fastapi import Depends
from core.dependencies import get_current_user

@router.post("/endpoint")
async def handler(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    user_id = current_user["user_id"]
```

### Async Database Session
**Apply to:** All repository and service files
```python
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from core.database import get_db

async def some_function(db: AsyncSession = Depends(get_db)):
    ...
```

### Error Handling
**Apply to:** All router handlers
```python
from fastapi import HTTPException, status

# 401 for auth failures
raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

# 404 for missing resources
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
```

### Structured Logging
**Apply to:** All service and router files
```python
import structlog
logger = structlog.get_logger()

logger.info("event_name", user_id=user_id, action="login")
```

### Import Path Convention
**Apply to:** All backend files
- Relative to `backend/` root: `from core.config import settings`
- Models: `from models.user import User`
- Repos: `from repositories.user_repo import get_user_by_email`
- Services: `from services.audit_service import create_audit_record`

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| All 28 files | various | various | Greenfield project -- no existing codebase. All patterns sourced from RESEARCH.md code examples and library documentation. |

## Anti-Patterns (from RESEARCH.md)

These must be avoided across all files:

| Anti-Pattern | Correct Pattern | Applies To |
|--------------|-----------------|------------|
| Post-retrieval filtering | Qdrant `must` filter at query time | vector_repo.py |
| Mutable audit via DELETE | Append/update only, never delete | audit_repo.py, audit_service.py |
| Secrets in source code | .env file + pydantic-settings | config.py, all files |
| Synchronous DB calls | AsyncSession everywhere | All repository/service files |
| passlib for hashing | pwdlib[bcrypt] | security.py |
| `declarative_base()` | `class Base(DeclarativeBase)` | models/base.py |
| Sync Alembic template | `alembic init -t async` | alembic/env.py |

## Metadata

**Analog search scope:** /Users/vmiu/Documents/Code/copinvest/ (entire project)
**Files scanned:** 0 source files (greenfield -- only .planning/ and CLAUDE.md exist)
**Pattern extraction date:** 2026-04-29
**Pattern sources:** RESEARCH.md code examples, CONTEXT.md locked decisions, library documentation
