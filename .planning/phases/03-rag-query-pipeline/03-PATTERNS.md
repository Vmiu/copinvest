# Phase 3: RAG Query Pipeline - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 10 (7 new, 3 modified)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/services/query_rewrite_service.py` | service | request-response | `backend/services/chunking_service.py` | exact |
| `backend/services/rerank_service.py` | service | request-response | `backend/services/embedding_service.py` | exact |
| `backend/services/generation_service.py` | service | request-response | `backend/services/chunking_service.py` | exact |
| `backend/services/query_service.py` | service | request-response | `backend/services/ingestion_service.py` | exact |
| `backend/routers/query.py` | router | request-response | `backend/routers/ingest.py` | exact |
| `backend/schemas/query.py` | schema | — | `backend/schemas/ingest.py` | exact |
| `alembic/versions/xxx_add_query_pipeline_fields.py` | migration | — | `alembic/versions/23b31f0ac9b4_add_document_registry.py` | exact |
| `backend/services/chunking_service.py` (modify) | service | request-response | self | — |
| `backend/models/audit_log.py` (modify) | model | — | self | — |
| `backend/services/audit_service.py` (modify) | service | — | self | — |
| `backend/services/session_service.py` (modify) | service | — | self | — |
| `backend/main.py` (modify) | app | — | self | — |

---

## Pattern Assignments

### `backend/services/query_rewrite_service.py` (service, request-response)

**Analog:** `backend/services/chunking_service.py`

**Imports pattern** (lines 1-7):
```python
import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

logger = structlog.get_logger()
```

**Core pattern — DeepSeek chat completion with retry** (lines 43-86):
```python
MAX_ATTEMPTS = 3

async def _chunk_page(page_text: str, prev_tail: str, client: AsyncOpenAI, semaphore: asyncio.Semaphore) -> list[str]:
    last_error = None
    async with semaphore:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": CHUNKING_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                )
                raw = response.choices[0].message.content.strip()
                # ... parse raw ...
                return result
            except ValueError:
                raise
            except (APIConnectionError, RateLimitError, APIError) as e:
                last_error = e
                logger.warning("chunking_retry", attempt=attempt + 1, error=str(e))
    raise RuntimeError(f"... failed after {MAX_ATTEMPTS} attempts: {last_error}")
```

**Key differences for query_rewrite_service:** Use `model="deepseek-chat"` (DeepSeek V4 Flash maps to this endpoint), no semaphore needed (single call, not parallel), return a single rewritten string instead of a list.

---

### `backend/services/rerank_service.py` (service, request-response)

**Analog:** `backend/services/embedding_service.py`

**Imports pattern** (lines 1-6):
```python
import httpx
import structlog
from backend.core.config import get_settings

logger = structlog.get_logger()
```

**Core pattern — httpx POST to external API** (lines 14-44):
```python
async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post(
            VOYAGE_EMBED_URL,
            headers={
                "Authorization": f"Bearer {settings.voyage_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VOYAGE_MODEL,
                "input": chunks,
                "input_type": "document",
            },
        )
        resp.raise_for_status()
    data = resp.json()
    vectors = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
    logger.info("embedding_complete", chunk_count=len(chunks), ...)
    return vectors
```

**Key differences for rerank_service:** URL is `https://openrouter.ai/api/v1/rerank`, key is `settings.openroute_api_key`, body uses `{"model": "cohere/rerank-v3.5", "query": query, "documents": texts}`, response shape is `data["results"]` sorted by `relevance_score`.

---

### `backend/services/generation_service.py` (service, request-response)

**Analog:** `backend/services/chunking_service.py`

**Core pattern — DeepSeek chat completion** (lines 62-86):
```python
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
    temperature=0.0,
)
raw = response.choices[0].message.content.strip()
```

**Key differences for generation_service:** Model string will be `"deepseek-reasoner"` (DeepSeek V4 Pro). Must also capture token usage: `response.usage.prompt_tokens`, `response.usage.completion_tokens`. Return a dict with `{"response": str, "prompt_tokens": int, "completion_tokens": int}`. No retry loop needed (single call, caller handles errors).

---

### `backend/services/query_service.py` (service, request-response)

**Analog:** `backend/services/ingestion_service.py`

**Imports pattern** (lines 1-18):
```python
import asyncio
import json
import time
from uuid import uuid4

import structlog
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories import ...
from backend.services import ...

logger = structlog.get_logger()
```

**Core orchestrator pattern** (lines 45-125):
```python
async def ingest_document(
    db: AsyncSession,
    ...,
    chunking_client: AsyncOpenAI,
    openrouter_client: AsyncOpenAI,
    qdrant_client: QdrantClient,
) -> dict:
    start = time.monotonic()
    logger.info("ingestion_started", ...)

    # Step 1
    result_1 = await service_a.do_thing(...)
    # Step 2
    result_2 = await service_b.do_thing(...)
    # Step 3 — write to DB
    await repo.upsert(db, record)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info("ingestion_complete", ..., duration_ms=elapsed_ms)
    return { ... }
```

**Key differences for query_service:** Steps are rewrite → embed query → retrieve from Qdrant → rerank → build prompt → generate. Audit record is created at start and updated at each step via `audit_service`. Returns `QueryResponse`-shaped dict.

---

### `backend/routers/query.py` (router, request-response)

**Analog:** `backend/routers/ingest.py`

**Imports pattern** (lines 1-13):
```python
import structlog
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_chunking_client, get_openrouter_client, get_qdrant_client, require_role
from backend.schemas.query import QueryRequest, QueryResponse
from backend.services import query_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["query"])
```

**Endpoint pattern** (lines 20-58):
```python
@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    sensitivity_tier: SensitivityTier = Form(...),
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
    chunking_client: AsyncOpenAI = Depends(get_chunking_client),
    openrouter_client: AsyncOpenAI = Depends(get_openrouter_client),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
):
    try:
        result = await ingestion_service.ingest_document(db=db, ...)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return result
```

**Key differences for query.py:** Body is JSON (`QueryRequest`), not form/file upload. `require_role` accepts `"adviser"`, `"senior_adviser"`, `"compliance"`. Status code is 200. `db.commit()` still called after service returns.

---

### `backend/schemas/query.py` (schema)

**Analog:** `backend/schemas/ingest.py`

**Pattern** (lines 1-14):
```python
from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    sensitivity_tier: int
    chunk_count: int
    total_chars: int
    warnings: list[str]
    parse_duration_ms: int
    extraction_method: str
```

**Key differences for query.py:** Add `QueryRequest(query: str, session_id: str | None, channel: str)` and `QueryResponse(trace_id: str, answer: str, sources: list[SourceRef], rewritten_query: str, model_used: str, prompt_tokens: int, completion_tokens: int)`. Add a `SourceRef` sub-model for citation objects.

---

### `alembic/versions/xxx_add_query_pipeline_fields.py` (migration)

**Analog:** `alembic/versions/23b31f0ac9b4_add_document_registry.py`

**Full migration pattern** (lines 1-49):
```python
"""add query pipeline fields

Revision ID: <generated>
Revises: 23b31f0ac9b4
Create Date: ...

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '<generated>'
down_revision: Union[str, Sequence[str], None] = '23b31f0ac9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_log', sa.Column('rewritten_query', sa.Text(), nullable=True))
    op.add_column('audit_log', sa.Column('rerank_scores', sa.Text(), nullable=True))
    op.add_column('sessions', sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_log', 'rewritten_query')
    op.drop_column('audit_log', 'rerank_scores')
    op.drop_column('sessions', 'last_activity')
```

**Note:** Use `op.add_column` (not `op.create_table`) since these are additions to existing tables. `down_revision` must be `'23b31f0ac9b4'` (current head).

---

## Shared Patterns

### Authentication / Role Guard
**Source:** `backend/core/dependencies.py` lines 66-74
**Apply to:** `backend/routers/query.py`
```python
def require_role(*allowed_roles: str):
    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' not authorized",
            )
        return current_user
    return _check
```

### Client Singleton Pattern
**Source:** `backend/core/dependencies.py` lines 11-50
**Apply to:** `backend/main.py` (registering new query client if needed), `backend/routers/query.py` (injecting clients)
```python
# Singletons initialised in lifespan, injected via Depends
_chunking_client: AsyncOpenAI | None = None

def get_chunking_client() -> AsyncOpenAI:
    if _chunking_client is None:
        raise RuntimeError("Chunking client not initialised")
    return _chunking_client
```
The generation client (DeepSeek V4 Pro) uses the same `deepseek_api_key` with `base_url="https://api.deepseek.com/v1"` — add a `_generation_client` singleton following this exact pattern.

### Structured Logging
**Source:** All service files, e.g. `backend/services/ingestion_service.py` lines 61, 113
**Apply to:** All new service files
```python
logger = structlog.get_logger()
logger.info("operation_started", key=value, ...)
logger.info("operation_complete", key=value, duration_ms=elapsed_ms)
logger.warning("operation_retry", attempt=attempt + 1, error=str(e))
```

### Error Propagation (service → router)
**Source:** `backend/routers/ingest.py` lines 52-55
**Apply to:** `backend/routers/query.py`
```python
try:
    result = await service.do_thing(...)
except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e))
except RuntimeError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

### DB Flush Pattern (audit updates)
**Source:** `backend/services/audit_service.py` lines 24-45
**Apply to:** `backend/services/audit_service.py` (new update functions), `backend/services/query_service.py`
```python
async def update_retrieval(db: AsyncSession, audit: AuditLog, ...) -> None:
    audit.field = value
    audit.status = AuditStatus.retrieved
    await db.flush()  # flush within transaction; caller commits
```

### Settings Access
**Source:** `backend/core/config.py` + `backend/services/embedding_service.py` line 19
**Apply to:** `backend/services/rerank_service.py`, `backend/services/generation_service.py`
```python
from backend.core.config import get_settings
settings = get_settings()
# Access: settings.openroute_api_key, settings.deepseek_api_key, settings.voyage_api_key
```

---

## Modified Files — Change Scope

### `backend/services/chunking_service.py`
**Change:** Update model string on line 66 from `"deepseek-chat"` to the new model identifier per RESEARCH.md. Single-line change.

### `backend/models/audit_log.py`
**Change:** Add new `Mapped` columns to `AuditLog` (e.g. `rewritten_query`, `rerank_scores`) following the existing nullable column pattern (lines 30-41). Add `last_activity` to `Session` model following `end_time` pattern (line 16).

### `backend/services/audit_service.py`
**Change:** Add a new `update_rewrite` function following the `update_retrieval` pattern (lines 24-32): assign fields, set status, `await db.flush()`.

### `backend/services/session_service.py`
**Change:** Update `SESSION_TIMEOUT` from 30 minutes to 24 hours (line 9). Add `last_activity` update on session reuse (line 26 area).

### `backend/main.py`
**Change:** Import and register query router following the ingest router pattern (lines 13, 52):
```python
from backend.routers.query import router as query_router
app.include_router(query_router)
```

---

## No Analog Found

All files have close analogs in the codebase.

---

## Metadata

**Analog search scope:** `backend/services/`, `backend/routers/`, `backend/schemas/`, `backend/models/`, `backend/repositories/`, `backend/core/`, `alembic/versions/`
**Files scanned:** 12
**Pattern extraction date:** 2026-05-07
