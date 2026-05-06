---
phase: 02-document-ingestion
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - backend/models/document.py
  - backend/repositories/document_repo.py
  - backend/schemas/ingest.py
  - backend/repositories/vector_repo.py
  - backend/core/config.py
  - backend/core/dependencies.py
  - backend/models/__init__.py
  - backend/services/chunking_service.py
  - backend/services/embedding_service.py
  - backend/services/ingestion_service.py
  - backend/routers/ingest.py
  - backend/main.py
  - tests/test_ingestion.py
  - tests/test_chunking.py
findings:
  critical: 3
  warning: 5
  info: 4
  total: 12
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-06
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the complete document ingestion pipeline: models, repositories, services (chunking, embedding, ingestion), the ingest router, application startup, and integration tests. Cross-referenced `backend/models/enums.py`, `backend/core/database.py`, and `pyproject.toml` for additional context.

The pipeline architecture is sound: docling parsing → LLM chunking → embedding → Qdrant upsert → SQL registry. The role-based access pattern is correctly structured and the re-ingestion (delete-then-insert) flow is logically correct. However, three blockers were found: a JWT validation gap that leaks auth state, a data-loss window during re-ingestion due to missing atomicity, and an unbounded file read that enables DoS. Five warnings cover correctness and robustness gaps.

---

## Critical Issues

### CR-01: JWT `role` claim not validated — wrong HTTP status and inconsistent auth state

**File:** `backend/core/dependencies.py:13-21`
**Issue:** `user_id` is checked for `None` (line 15) and raises 401 when absent, but `role` is not. If a validly-signed JWT contains `sub` but no `role` claim, `payload.get("role")` returns `None`, the function does not raise, and it returns `{"user_id": ..., "role": None}`. `require_role("compliance")` then evaluates `None not in ("compliance",)` → `True` → raises **403 Forbidden** instead of **401 Unauthorized**. A 403 tells the client "you're authenticated but not authorized," which is factually wrong for a token that is structurally invalid. In a compliance-grade application this auth-state inconsistency is a defect — any endpoint without role enforcement could also receive this user dict with `role=None`.

**Fix:**
```python
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"user_id": user_id, "role": role}
```

---

### CR-02: No atomicity between Qdrant delete and insert — data loss window on re-ingestion

**File:** `backend/services/ingestion_service.py:89-99`
**Issue:** Re-ingestion (D-12) follows: `delete_by_source` (line 89) then `upsert_chunks` (line 99). These are two independent operations against two separate systems (Qdrant and SQL). If `upsert_chunks` fails — network error, Qdrant OOM, any exception — after `delete_by_source` has already committed to Qdrant, the document's chunks are permanently gone. The SQL registry record still exists (from the prior ingestion or the current flush) but points to a Qdrant collection that has zero chunks for that `source_id`. The document becomes un-queryable with no error surfaced to the caller.

There is no compensation, retry, or rollback path. The `db.flush()` in `document_repo.upsert_document_record` and the `db.commit()` in the router occur after the Qdrant writes, so DB rollback cannot undo the Qdrant deletions.

**Fix:** Reverse the order so that new chunks are written before old ones are removed (write-then-replace rather than delete-then-write), and only delete old chunks after the new upsert succeeds:

```python
# 5a. Upsert NEW chunks first
chunk_count = vector_repo.upsert_chunks(qdrant, chunks, vectors, payload_base)

# 5b. Only after new chunks are confirmed written, delete the old ones
vector_repo.delete_by_source_except_new(qdrant, doc_id, new_point_ids)
```

If write-then-selective-delete is not feasible with the current `upsert_chunks` signature (which generates random UUIDs internally), an alternative is to stage new chunks under a temporary `source_id`, verify the count, then atomically swap and delete the old `source_id`. At minimum, a post-`upsert_chunks` verification check on the returned point count before deleting old chunks would catch partial failures.

---

### CR-03: No file size limit — unbounded memory allocation on upload

**File:** `backend/routers/ingest.py:24`
**Issue:** `content = await file.read()` reads the entire uploaded file into memory with no upper bound. A compliance user (authenticated but adversarial, or simply mistaken) can upload a multi-gigabyte file, causing the process to OOM or the server to become unresponsive. The in-memory buffer is then held through parsing, chunking, and embedding — potentially three copies of the file content in memory simultaneously (the raw bytes, docling's internal representation, and the resulting markdown).

**Fix:** Enforce a size limit before reading the full content. A streaming size check is safe:

```python
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB — adjust to operational reality

content = await file.read(MAX_UPLOAD_BYTES + 1)
if len(content) > MAX_UPLOAD_BYTES:
    raise HTTPException(
        status_code=413,
        detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)} MB",
    )
if not content:
    raise HTTPException(status_code=400, detail="Empty file")
```

Alternatively, configure a global `MAX_REQUEST_BODY_SIZE` in uvicorn or middleware so the limit is enforced before the handler is reached.

---

## Warnings

### WR-01: Retry loop in `chunk_document` retries non-transient errors

**File:** `backend/services/chunking_service.py:22-43`
**Issue:** The `except Exception` at line 39 catches all exceptions including `ValueError("LLM returned no chunks")` raised at line 36. An empty LLM response is a logic failure that cannot be resolved by retrying the same input three times. Every retry makes an unnecessary OpenAI API call, burning tokens and adding ~10s of latency before surfacing a RuntimeError that could have been raised immediately.

**Fix:** Separate transient errors (API/network) from logic errors:

```python
from openai import APIError, APIConnectionError, RateLimitError

async def chunk_document(markdown: str, client: AsyncOpenAI) -> list[str]:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.chat.completions.create(...)
            raw = response.choices[0].message.content
            chunks = [c.strip() for c in raw.split("\n---\n") if c.strip()]
            if not chunks:
                raise ValueError("LLM returned no chunks")
            return chunks
        except ValueError:
            raise  # non-transient: propagate immediately
        except (APIConnectionError, RateLimitError, APIError) as e:
            last_error = e
            logger.warning("chunking_retry", attempt=attempt + 1, error=str(e))
    raise RuntimeError(f"Chunking failed after {MAX_ATTEMPTS} attempts: {last_error}")
```

---

### WR-02: Chunk splitter is fragile when LLM output starts with `---`

**File:** `backend/services/chunking_service.py:34`
**Issue:** `raw.split("\n---\n")` requires the separator to have a leading newline. If the LLM begins its response with `---\nFirst chunk\n---\nSecond chunk`, the split produces `["---\nFirst chunk", "Second chunk"]` — the first element incorrectly includes the literal separator. The `if c.strip()` filter does not help here because the element is non-empty. This is a realistic failure mode: some LLM outputs trim leading whitespace and may start the response immediately with `---`.

**Fix:** Normalize the raw output before splitting:

```python
raw = response.choices[0].message.content.strip()
# Normalize to ensure consistent separator format regardless of LLM whitespace behavior
normalized = raw.replace("\r\n", "\n")
# Split on any line that is exactly "---"
import re
parts = re.split(r'\n?^---$\n?', normalized, flags=re.MULTILINE)
chunks = [c.strip() for c in parts if c.strip()]
```

---

### WR-03: `embed_chunks` has no guard against empty input

**File:** `backend/services/embedding_service.py:7-14`
**Issue:** `embed_chunks([], client)` passes an empty list to `client.embeddings.create(model=..., input=[])`. The OpenAI API returns an error for empty `input`. The function does not validate this case, so a caller that somehow reaches `embed_chunks` with an empty chunk list gets an unhandled API error that surfaces as a generic 500 instead of a descriptive error. The `if vectors` guard on line 13 only protects the log line, not the API call.

**Fix:**
```python
async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    if not chunks:
        raise ValueError("embed_chunks called with empty chunk list")
    response = await client.embeddings.create(model="text-embedding-3-small", input=chunks)
    ...
```

---

### WR-04: OpenAI and Qdrant clients created per ingestion request

**File:** `backend/services/ingestion_service.py:79,88`
**Issue:** Both `AsyncOpenAI(api_key=...)` (line 79) and `vector_repo.get_qdrant_client()` (line 88) are instantiated on every call to `ingest_document`. `AsyncOpenAI` manages its own connection pool internally; constructing it per-request creates and tears down the pool on every call, wasting TCP connections and TLS handshakes. `QdrantClient` similarly opens a new connection per request.

**Fix:** Promote both clients to application-lifetime singletons. The `AsyncOpenAI` client is thread-safe and async-safe. Inject them via FastAPI dependencies or module-level singletons created during `lifespan`:

```python
# In lifespan or a dedicated module:
_openai_client: AsyncOpenAI | None = None
_qdrant_client: QdrantClient | None = None

def get_openai_client() -> AsyncOpenAI:
    return _openai_client

def get_qdrant_client() -> QdrantClient:
    return _qdrant_client
```

Then inject them into `ingest_document` rather than constructing them inline.

---

### WR-05: Qdrant startup failure swallows exception details

**File:** `backend/main.py:23-27`
**Issue:** The `except Exception:` block during startup logs a static message but discards the actual exception. If Qdrant is misconfigured (wrong host, wrong port, wrong API key, TLS error), the startup log shows only "Qdrant not available at startup — collection setup skipped" with no indication of root cause. Diagnosing production startup failures requires guessing.

**Fix:**
```python
except Exception as exc:
    logger.warning(
        "qdrant_init_failed",
        msg="Qdrant not available at startup — collection setup skipped",
        error=str(exc),
        error_type=type(exc).__name__,
    )
```

---

## Info

### IN-01: `TIER_TO_ROLES` type annotation is misleading

**File:** `backend/services/ingestion_service.py:21-26`
**Issue:** The annotation is `dict[int, list[str]]` but the keys are `SensitivityTier` enum instances (e.g., `SensitivityTier.public`). This works at runtime because `SensitivityTier` is an `int` subclass and Python's dict hashing treats `SensitivityTier.public == 1` as True. But the annotation misrepresents the actual key type and the `TIER_TO_ROLES.get(sensitivity_tier.value, ...)` call on line 92 (passing an `int` to look up an `IntEnum` key) is needlessly inconsistent — it works, but a reader must understand IntEnum equality to verify it.

**Fix:** Either use consistent enum keys throughout or use `int` keys consistently:
```python
TIER_TO_ROLES: dict[SensitivityTier, list[str]] = {
    SensitivityTier.public: [...],
    ...
}
# lookup:
allowed_roles = TIER_TO_ROLES.get(sensitivity_tier, ["compliance"])
```

---

### IN-02: Integration tests do not verify SQL registry persistence

**File:** `tests/test_ingestion.py:138-165` (and similar tests)
**Issue:** Tests like `test_ingest_pdf_success`, `test_reingest_replaces_chunks`, and `test_ingest_quality_metrics` verify HTTP response bodies and Qdrant state but never assert that a `DocumentRecord` was written to the SQL database. If `document_repo.upsert_document_record` silently fails or if the `db.commit()` in the router is accidentally removed, all ingestion tests still pass.

**Fix:** Add a DB verification step to the critical path tests:
```python
from backend.repositories.document_repo import get_document_by_id

record = await get_document_by_id(db_session_ingest, body["document_id"])
assert record is not None
assert record.chunk_count == len(_MOCK_CHUNKS)
```

---

### IN-03: No test coverage for `sensitivity_tier=4` (confidential)

**File:** `tests/test_ingestion.py`
**Issue:** The `TIER_TO_ROLES` mapping for tier 4 (confidential) restricts access to `["compliance"]` only. There is no test verifying that a confidential document's Qdrant points have `allowed_roles == ["compliance"]`. Given that this is the most sensitive tier, its access-control mapping deserves its own test case mirroring `test_ingest_sensitivity_tier_stored`.

**Fix:** Add a test case:
```python
async def test_ingest_confidential_tier_rbac(ingest_client, compliance_user, qdrant_memory):
    """Tier 4 (confidential) chunks must only be accessible to compliance role."""
    # ... upload with sensitivity_tier=4
    # ... scroll Qdrant, assert allowed_roles == ["compliance"]
```

---

### IN-04: `Base.metadata.create_all` in lifespan bypasses Alembic migration tracking

**File:** `backend/main.py:17-18`
**Issue:** Running `Base.metadata.create_all` on every startup creates tables that SQLAlchemy knows about but Alembic does not track. When a schema migration is later run via `alembic upgrade head`, Alembic may detect drift or fail with "table already exists" depending on migration script style. In production with an existing database, `create_all` is a no-op (tables exist) — meaning new columns added in later migrations will not be applied by startup alone, creating a silent schema mismatch.

**Fix:** For production, rely exclusively on `alembic upgrade head` in the deployment pipeline. For development convenience, keep `create_all` but add a comment making clear it is dev-only scaffolding:
```python
# Dev-only: create tables directly. In production, use: uv run alembic upgrade head
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

---

_Reviewed: 2026-05-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
