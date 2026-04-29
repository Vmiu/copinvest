# Phase 1: Data Foundation - Research

**Researched:** 2026-04-29
**Domain:** Authentication, RBAC, audit schema, Qdrant/SQLite infrastructure
**Confidence:** HIGH

## Summary

Phase 1 establishes the security and data foundation for CopInvest: JWT-based authentication, role-based access control with three fixed roles mapped to four sensitivity tiers, a progressive audit log schema, and the Qdrant vector store infrastructure. Every subsequent phase depends on these primitives.

The stack is well-defined by locked decisions: FastAPI + SQLAlchemy async (SQLite for dev) + Qdrant (Docker) + PyJWT for tokens. One critical finding: **passlib is broken on Python 3.13** (the runtime on this machine). Use `pwdlib` with bcrypt instead. Qdrant v1.17.1 supports pre-filtering on payload arrays via `MatchValue`/`MatchAny`, which is the correct pattern for RBAC at the vector store layer.

**Primary recommendation:** Build auth middleware and audit schema first (they gate everything), then Qdrant collection setup with payload indexes on `allowed_roles` and `sensitivity_tier`, then seed users from a JSON config file.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SQLite for local dev. SQLAlchemy abstracts dialect difference from production PostgreSQL.
- **D-02:** Qdrant runs as Docker container. Use `qdrant-client` Python SDK.
- **D-03:** `docker-compose.yml` with Qdrant service. SQLite file in project directory.
- **D-04:** Three fixed roles: `adviser`, `senior_adviser`, `compliance`.
- **D-05:** Strict hierarchy: adviser -> tier 1; senior_adviser -> tiers 1-3; compliance -> tiers 1-4.
- **D-06:** Users seeded via config file. Contains email, hashed password, role.
- **D-07:** Role stored in JWT payload -- no DB lookup per query.
- **D-08:** Progressive audit record lifecycle (created on query, updated on retrieval, on LLM response, on adviser action).
- **D-09:** Sessions: 30-min inactivity timeout with session_id, start_time, end_time.
- **D-10:** Audit records include sensitivity_tier_accessed (max tier of retrieved chunks).

### Claude's Discretion
- Exact SQLAlchemy model field types and indexes
- Alembic migration structure
- JWT token expiry duration and refresh strategy
- Seed file format (JSON vs YAML)
- Qdrant collection configuration (distance metric, vector size)

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Login with email/password, receive JWT | OAuth2PasswordBearer + PyJWT + pwdlib[bcrypt] |
| AUTH-02 | Session persists via stored JWT | JWT with configurable expiry (recommend 24h) |
| AUTH-03 | Role determines document access | User model with role enum; role in JWT |
| AUTH-04 | Pre-retrieval filtering by role | Qdrant `must` filter with `MatchAny` on `allowed_roles` |
| AUTH-05 | Adviser cannot access Restricted/Confidential | `allowed_roles` excludes `adviser` for tiers 3-4 |
| AUDIT-01 | Full trace audit record per query | AuditLog model with progressive updates |
| AUDIT-02 | Records grouped by session | Session model; 30-min inactivity timeout |
| AUDIT-03 | Pinned model version in record | `model_used` field |
| AUDIT-04 | Adviser action recorded | `adviser_action` enum; PATCH endpoint |
| AUDIT-05 | Sensitivity tier per query | `sensitivity_tier_accessed` integer |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JWT authentication | API / Backend | -- | Token issuance/validation server-side only |
| Password hashing | API / Backend | -- | bcrypt server-side only |
| RBAC filtering | Database (Qdrant) | API / Backend | Qdrant pre-filters; backend injects role |
| Audit log persistence | Database (SQLite/PG) | API / Backend | SQLAlchemy via BackgroundTasks |
| Session management | API / Backend | -- | Server tracks session_id and timeout |
| User seeding | API / Backend | -- | CLI script reads seed file |
| Qdrant collection setup | Database (Qdrant) | API / Backend | Created at startup or via script |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.136.1 | REST API | [VERIFIED: pip] Async-native, Pydantic v2, OAuth2 |
| SQLAlchemy | 2.0.49 | Async ORM | [VERIFIED: pip] AsyncSession, dialect abstraction |
| aiosqlite | 0.22.1 | Async SQLite driver | [VERIFIED: pip] Required for async SQLite |
| Alembic | 1.18.4 | DB migrations | [VERIFIED: pip] Has async template |
| qdrant-client | 1.17.1 | Qdrant SDK | [VERIFIED: pip] Matches server v1.17.1 |
| PyJWT | 2.12.1 | JWT encode/decode | [VERIFIED: pip] Lightweight |
| pwdlib[bcrypt] | 0.3.0 | Password hashing | [VERIFIED: pip] Replaces broken passlib |
| pydantic-settings | 2.14.0 | Config from env | [VERIFIED: pip] .env support |
| structlog | 25.5.0 | Structured logging | [VERIFIED: pip] JSON logs |

### Dev/Test

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | 8.4.2 | Test framework |
| pytest-asyncio | 0.26.0 | Async test support |
| httpx | 0.28.1 | Async test client |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | Unnecessary JWS/JWE overhead |
| pwdlib | passlib | Broken on Python 3.13 |
| pwdlib | raw bcrypt | pwdlib adds hash upgrade logic |

**Installation:**
```bash
pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" aiosqlite alembic \
  qdrant-client pyjwt "pwdlib[bcrypt]" pydantic-settings structlog \
  pytest "pytest-asyncio==0.26.0" httpx
```
## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────────┐
                    │           FastAPI Application             │
                    │                                          │
  POST /auth/token  │  ┌─────────┐    ┌──────────────────┐   │
  ─────────────────>│  │  Auth   │───>│  User Repository  │──>│──> SQLite (users)
                    │  │ Router  │    │  (SQLAlchemy)     │   │
                    │  └─────────┘    └──────────────────┘   │
                    │                                          │
  POST /api/v1/query│  ┌─────────┐    ┌──────────────────┐   │
  ─────────────────>│  │  Auth   │───>│  JWT Middleware   │   │
  (Bearer JWT)      │  │Middleware│   │  (decode + role)  │   │
                    │  └────┬────┘    └──────────────────┘   │
                    │       │                                  │
                    │       v                                  │
                    │  ┌─────────────────────────────────┐    │
                    │  │         RAG Service              │    │
                    │  │  1. Embed query (OpenAI)         │    │
                    │  │  2. Qdrant query + role filter   │───>│──> Qdrant (Docker)
                    │  │  3. Build prompt                 │    │
                    │  │  4. LLM generation (OpenAI)      │    │
                    │  └────────────┬────────────────────┘    │
                    │               │                          │
                    │               v                          │
                    │  ┌─────────────────────────────────┐    │
                    │  │       Audit Service              │───>│──> SQLite (audit_log)
                    │  │  (BackgroundTasks write)         │    │
                    │  └─────────────────────────────────┘    │
                    └──────────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/
├── main.py                    # App factory, lifespan (DB + Qdrant init)
├── core/
│   ├── config.py              # Settings (pydantic-settings, env vars)
│   ├── database.py            # AsyncEngine + async_sessionmaker
│   ├── security.py            # JWT encode/decode, password hashing
│   └── dependencies.py        # Depends: get_db, get_current_user
├── routers/
│   ├── auth.py                # POST /api/v1/auth/token
│   └── query.py               # POST /api/v1/query (placeholder for Phase 3)
├── services/
│   ├── audit_service.py       # Create/update audit records
│   └── session_service.py     # Session tracking (30-min timeout)
├── repositories/
│   ├── user_repo.py           # User lookups
│   ├── audit_repo.py          # Audit log CRUD
│   └── vector_repo.py         # Qdrant collection setup + filtered queries
├── models/
│   ├── base.py                # DeclarativeBase
│   ├── user.py                # User SQLAlchemy model
│   ├── audit_log.py           # AuditLog + Session models
│   └── enums.py               # UserRole, SensitivityTier, AdviserAction
├── schemas/
│   ├── auth.py                # TokenRequest, TokenResponse
│   └── audit.py               # AuditRecord schemas
├── scripts/
│   └── seed_users.py          # Load users from seed file
├── alembic/                   # Migrations (async template)
│   ├── env.py
│   └── versions/
├── alembic.ini
├── docker-compose.yml         # Qdrant service
├── seed_users.json            # User seed data
└── .env                       # Local config (not committed)
```

### Pattern 1: FastAPI OAuth2 + JWT Authentication
**What:** OAuth2PasswordBearer scheme with PyJWT for token creation/validation
**When:** Every authenticated endpoint
**Example:**
```python
# Source: FastAPI docs + PyJWT docs
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": user_id, "role": role}
```

### Pattern 2: Qdrant Pre-Filtering by Role
**What:** Inject user role as a `must` filter condition on `allowed_roles` payload field
**When:** Every vector search query
**Example:**
```python
# Source: Qdrant filtering docs + qdrant-client SDK
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

def query_with_rbac(client: QdrantClient, query_vector: list[float],
                    user_role: str, collection: str, limit: int = 20):
    return client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="allowed_roles",
                    match=MatchValue(value=user_role),
                )
            ]
        ),
        limit=limit,
    )
```

### Pattern 3: Progressive Audit Record
**What:** Create audit record at query start, update as pipeline progresses
**When:** Every query through the RAG pipeline
**Example:**
```python
# Create on query receipt
audit = AuditLog(trace_id=uuid4(), user_id=user_id, query_text=query,
                 session_id=session_id, channel="web")
session.add(audit)
await session.commit()

# Update after retrieval
audit.retrieved_chunks = retrieved_chunks_json
audit.sensitivity_tier_accessed = max(chunk.tier for chunk in chunks)
await session.commit()

# Update after LLM response
audit.llm_response = response_text
audit.model_used = "gpt-4o-2024-11-20"
audit.prompt_sent = prompt_text
await session.commit()
```

### Anti-Patterns to Avoid
- **Post-retrieval filtering:** Never retrieve all docs then filter by role. Qdrant must filter at query time.
- **Mutable audit records via DELETE:** Audit records are append/update only. Never delete.
- **Storing secrets in code:** JWT secret, DB credentials in .env only, never in source.
- **Synchronous DB calls:** All SQLAlchemy operations must use AsyncSession.
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | pwdlib[bcrypt] | Timing attacks, salt management, upgrade paths |
| JWT tokens | Custom token format | PyJWT with HS256 | Token validation, expiry, standard claims |
| OAuth2 flow | Custom auth headers | FastAPI OAuth2PasswordBearer | Standard flow, Swagger UI integration |
| DB migrations | Manual ALTER TABLE | Alembic (async template) | Version tracking, rollback, team coordination |
| Config management | os.environ reads | pydantic-settings | Validation, type coercion, .env file support |
| Structured logging | print/logging.info | structlog | JSON output, context binding, processor pipeline |

**Key insight:** Auth and audit are solved problems with well-tested libraries. Custom implementations introduce security vulnerabilities and compliance gaps.

## Common Pitfalls

### Pitfall 1: passlib Broken on Python 3.13
**What goes wrong:** `passlib` imports fail on Python 3.13 because it depends on the removed `crypt` module.
**Why it happens:** passlib is unmaintained since 2022. Python 3.13 removed `crypt` (PEP 594).
**How to avoid:** Use `pwdlib[bcrypt]` instead. Drop-in replacement with similar API.
**Warning signs:** `ImportError: No module named 'crypt'` at startup.
**Confidence:** HIGH [VERIFIED: pwdlib PyPI page explicitly states this]

### Pitfall 2: SQLite Async Requires aiosqlite Driver
**What goes wrong:** `create_async_engine("sqlite:///app.db")` fails -- needs async driver.
**Why it happens:** SQLAlchemy async requires an async-compatible DBAPI driver.
**How to avoid:** Use `sqlite+aiosqlite:///./app.db` as the connection string. Install `aiosqlite`.
**Warning signs:** `InvalidRequestError: The asyncio extension requires an async driver`.
**Confidence:** HIGH [CITED: SQLAlchemy 2.0 asyncio docs]

### Pitfall 3: Alembic Async Template Required
**What goes wrong:** Default `alembic init` generates sync `env.py` that fails with async engine.
**Why it happens:** Alembic defaults to sync. Must use `alembic init -t async alembic`.
**How to avoid:** Initialize with async template: `alembic init -t async alembic`.
**Warning signs:** `MissingGreenlet` error when running migrations.
**Confidence:** HIGH [CITED: Alembic async template on GitHub]

### Pitfall 4: Qdrant Payload Index Not Created
**What goes wrong:** Filtering works but is slow because payload fields are not indexed.
**Why it happens:** Qdrant does not auto-index payload fields. Must create indexes explicitly.
**How to avoid:** After collection creation, call `create_payload_index` for `allowed_roles` and `sensitivity_tier`.
**Warning signs:** Slow filtered queries on collections with >1000 points.
**Confidence:** HIGH [CITED: Qdrant payload indexing docs]

### Pitfall 5: JWT Secret Key Too Short or Predictable
**What goes wrong:** JWT tokens can be forged if the secret is weak.
**Why it happens:** Dev shortcuts -- using "secret" or short strings as JWT_SECRET.
**How to avoid:** Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. Store in .env.
**Warning signs:** Any JWT_SECRET shorter than 32 characters.
**Confidence:** HIGH [ASSUMED -- standard security practice]

### Pitfall 6: Progressive Audit Updates Lost on Crash
**What goes wrong:** If the app crashes between audit record creation and final update, partial records exist.
**Why it happens:** D-08 specifies progressive updates (multiple commits per record).
**How to avoid:** Each commit is a checkpoint. Partial records are acceptable -- they show how far the pipeline got. Add a `status` enum field (received/retrieved/generated/completed) to track progress.
**Warning signs:** Audit records with null `llm_response` or `retrieved_chunks`.
**Confidence:** MEDIUM [ASSUMED -- design recommendation]

## Code Examples

### Async SQLAlchemy Database Setup
```python
# backend/core/database.py
# Source: SQLAlchemy 2.0 asyncio docs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

### Password Hashing with pwdlib
```python
# backend/core/security.py
# Source: pwdlib docs (frankie567.github.io/pwdlib)
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)
```

### Qdrant Collection Setup
```python
# backend/repositories/vector_repo.py
# Source: Qdrant quickstart docs + filtering docs
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PayloadSchemaType
)

def setup_collection(client: QdrantClient, collection_name: str = "documents"):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    # Index payload fields used in RBAC filtering
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
```

### Docker Compose for Qdrant
```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:v1.17.1
    ports:
      - "6333:6333"   # REST API
      - "6334:6334"   # gRPC
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
```
## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| passlib for password hashing | pwdlib[bcrypt] | 2024 (passlib abandoned) | Must use pwdlib on Python 3.13+ |
| SQLAlchemy 1.x sync sessions | SQLAlchemy 2.0 AsyncSession | 2023 | All DB code uses async/await |
| `declarative_base()` function | `class Base(DeclarativeBase)` | SQLAlchemy 2.0 | New declarative style |
| ChromaDB for vector store | Qdrant with pre-filtering | Project decision | Security-correct RBAC model |
| `alembic init` (sync) | `alembic init -t async` | Alembic 1.12+ | Required for async engines |

**Deprecated/outdated:**
- passlib: Abandoned, broken on Python 3.13. Use pwdlib.
- python-jose: Heavier than needed. PyJWT is sufficient for HS256 JWT.
- `sessionmaker` (sync): Use `async_sessionmaker` with `AsyncSession`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JWT expiry of 24h is appropriate for this use case | Discretion | Too long = security risk; too short = UX friction. User should confirm. |
| A2 | JSON is better than YAML for seed file | Discretion | Minimal risk -- either works. JSON needs no extra dependency. |
| A3 | Cosine distance is correct for text-embedding-3-small | Qdrant config | Wrong metric = degraded retrieval quality. OpenAI recommends cosine. |
| A4 | HS256 is sufficient for JWT signing | Security | Symmetric key is fine for single-server. Would need RS256 for distributed. |
| A5 | pytest-asyncio 0.26.0 is more stable than 1.x | Dev/Test | 1.x may work fine; 0.26.0 is battle-tested. Low risk either way. |

## Open Questions

1. **SFC audit retention period**
   - What we know: PITFALLS.md mentions "typically 7 years" for investment advice records in HK
   - What's unclear: Exact requirement from primary SFC source. STATE.md flags this as open.
   - Recommendation: Design schema to support long retention (partitioning-ready). Confirm exact period before production. Does not block Phase 1 implementation.

2. **JWT refresh strategy**
   - What we know: D-07 says role in JWT. AUTH-02 says session persists across refresh.
   - What's unclear: Should we use refresh tokens or just long-lived access tokens?
   - Recommendation: Start with 24h access tokens, no refresh tokens. Simpler for v1 prototype. Add refresh tokens if needed later.

3. **Audit record immutability vs progressive updates**
   - What we know: D-08 specifies progressive updates. ARCHITECTURE.md Pattern 2 says INSERT-only.
   - What's unclear: These conflict. Progressive updates require UPDATE; immutability requires INSERT-only.
   - Recommendation: For v1, use UPDATE (progressive). Immutable append-only is a v2 requirement (AUDIT-V2-01). Document this as a known v1 limitation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All backend code | Yes | 3.13.12 | -- |
| Docker | Qdrant container | Yes | 29.4.0 | -- |
| Node.js | Frontend (future phases) | Yes | 24.15.0 | -- |
| pip | Package installation | Yes | 26.0.1 | -- |
| Qdrant (Docker image) | Vector store | Not pulled yet | v1.17.1 target | `docker pull qdrant/qdrant:v1.17.1` |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** Qdrant Docker image needs to be pulled (trivial).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio 0.26.0 |
| Config file | None -- Wave 0 creates `pyproject.toml` [tool.pytest] section |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Login returns JWT | integration | `pytest tests/test_auth.py::test_login_success -x` | Wave 0 |
| AUTH-01 | Bad password rejected | integration | `pytest tests/test_auth.py::test_login_bad_password -x` | Wave 0 |
| AUTH-03 | JWT contains role | unit | `pytest tests/test_security.py::test_jwt_contains_role -x` | Wave 0 |
| AUTH-04 | Qdrant filter includes role | unit | `pytest tests/test_vector_repo.py::test_rbac_filter -x` | Wave 0 |
| AUTH-05 | Adviser cannot access tier 3-4 | integration | `pytest tests/test_vector_repo.py::test_adviser_blocked -x` | Wave 0 |
| AUDIT-01 | Query creates audit record | integration | `pytest tests/test_audit.py::test_audit_created -x` | Wave 0 |
| AUDIT-02 | Session grouping works | unit | `pytest tests/test_session.py::test_session_timeout -x` | Wave 0 |
| AUDIT-05 | Tier recorded in audit | integration | `pytest tests/test_audit.py::test_tier_recorded -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- pytest configuration section
- [ ] `tests/conftest.py` -- async fixtures (test DB, test client, seed users)
- [ ] `tests/test_auth.py` -- AUTH-01, AUTH-02 tests
- [ ] `tests/test_security.py` -- JWT encode/decode, password hash tests
- [ ] `tests/test_vector_repo.py` -- AUTH-04, AUTH-05 Qdrant filter tests
- [ ] `tests/test_audit.py` -- AUDIT-01, AUDIT-05 tests
- [ ] `tests/test_session.py` -- AUDIT-02 session timeout tests
- [ ] Framework install: `pip install pytest "pytest-asyncio==0.26.0" httpx`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | PyJWT HS256 + pwdlib[bcrypt] + OAuth2PasswordBearer |
| V3 Session Management | Yes | JWT expiry + session inactivity timeout (30 min) |
| V4 Access Control | Yes | Qdrant pre-filtering on `allowed_roles` payload |
| V5 Input Validation | Yes | Pydantic v2 request validation (FastAPI built-in) |
| V6 Cryptography | No | No custom crypto -- JWT signing uses PyJWT |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| JWT token theft | Spoofing | Short expiry, HTTPS only, no token in URL params |
| Weak JWT secret | Tampering | 256-bit random secret from `secrets.token_hex(32)` |
| Post-retrieval filtering bypass | Info Disclosure | Qdrant `must` filter at query time (pre-retrieval) |
| Audit log tampering | Repudiation | DB-level write-only access for app user (v2: INSERT-only) |
| Brute force login | Elevation | Rate limiting on /auth/token endpoint |
| Secret in source code | Info Disclosure | .env file + .gitignore; pydantic-settings for config |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: pip registry] -- FastAPI 0.136.1, SQLAlchemy 2.0.49, qdrant-client 1.17.1, PyJWT 2.12.1, pwdlib 0.3.0, Alembic 1.18.4, pydantic-settings 2.14.0, structlog 25.5.0, aiosqlite 0.22.1
- [VERIFIED: GitHub API] -- Qdrant server v1.17.1 released 2026-03-27
- [CITED: SQLAlchemy 2.0 asyncio docs] -- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- [CITED: Alembic async template] -- https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py
- [CITED: Qdrant filtering docs] -- https://qdrant.tech/documentation/concepts/filtering/
- [CITED: pwdlib docs] -- https://frankie567.github.io/pwdlib/

### Secondary (MEDIUM confidence)
- FastAPI JWT auth patterns -- https://www.buanacoding.com/2025/08/fastapi-jwt-auth-oauth2-password-flow-pydantic-v2-sqlalchemy-2.html
- Qdrant quickstart -- https://qdrant.tech/documentation/quickstart/
- FastAPI async testing -- https://praciano.com.br/fastapi-and-async-sqlalchemy-20-with-pytest-done-right.html

### Tertiary (LOW confidence)
- None -- all claims verified or cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against pip registry
- Architecture: HIGH -- patterns from official docs and locked decisions
- Pitfalls: HIGH -- passlib/Python 3.13 verified; Qdrant patterns from official docs

**Research date:** 2026-04-29
**Valid until:** 2026-05-29 (stable stack, 30-day window)
