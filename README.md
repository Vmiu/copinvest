# CopInvest

A GenAI assistant for investment advisers in Hong Kong. Uses retrieval-augmented generation (RAG) over approved internal documents to prepare meeting briefs, summarise product information, and draft compliant follow-up notes.

## What it does

- Ingests PDF, Word (.docx), and Excel/CSV documents into a vector store
- PDFs are parsed page-by-page using a vision LLM (`qwen/qwen3-vl-32b`) — handles multi-column layouts, tables, charts, and KPI callout boxes
- Non-PDF files are parsed with docling
- Chunks are embedded with Voyage AI `voyage-3` (1024-dim, multilingual, full Chinese/CJK support)
- Role-based access control: advisers, senior advisers, and compliance officers see different document tiers
- Full audit trail of every query and ingestion

## Architecture

```
Client → FastAPI → ingestion_service
                       ├── document_parser  (PyMuPDF → qwen3-vl-32b via OpenRouter)
                       ├── chunking_service (DeepSeek chat)
                       ├── embedding_service (Voyage AI voyage-3)
                       └── vector_repo      (Qdrant)
```

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.13+ | |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | any | For Qdrant |
| DeepSeek API key | — | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| OpenRouter API key | — | [openrouter.ai](https://openrouter.ai/settings/keys) — needs credit for `qwen/qwen3-vl-32b-instruct` |
| Voyage AI API key | — | [voyageai.com](https://dashboard.voyageai.com/api-keys) — free tier covers 200M tokens/month |

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd copinvest
uv venv
uv pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the three required keys:

```
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DEEPSEEK_API_KEY=sk-...
OPENROUTE_API_KEY=sk-or-...
VOYAGE_API_KEY=pa-...
```

### 3. Start Qdrant

```bash
docker compose up -d
```

Qdrant will be available at `http://localhost:6333`. Data is persisted in a Docker volume (`qdrant_data`).

### 4. Run the server

```bash
uv run uvicorn backend.main:app --reload
```

The API is now at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

On first startup the server automatically creates the SQLite database tables and the Qdrant collection.

## Creating users

There is no sign-up endpoint — users are created directly in the database. Three roles exist: `adviser`, `senior_adviser`, `compliance`. Only `compliance` users can ingest documents.

```python
# uv run python
from backend.core.database import async_session, engine
from backend.models.base import Base
from backend.models.user import User
from backend.core.security import hash_password
import asyncio

async def create_user():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as db:
        user = User(
            id="user-001",
            email="alice@example.com",
            hashed_password=hash_password("yourpassword"),
            role="compliance",
        )
        db.add(user)
        await db.commit()

asyncio.run(create_user())
```

## API usage

### Authenticate

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=alice@example.com&password=yourpassword"
# → {"access_token": "eyJ...", "token_type": "bearer"}
```

### Ingest a document

Requires `compliance` role. `sensitivity_tier` controls which roles can retrieve chunks:

| Tier | Value | Readable by |
|---|---|---|
| public | 1 | adviser, senior_adviser, compliance |
| internal | 2 | senior_adviser, compliance |
| restricted | 3 | senior_adviser, compliance |
| confidential | 4 | compliance only |

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer <token>" \
  -F "file=@annual-report.pdf" \
  -F "sensitivity_tier=1"
```

Response:

```json
{
  "document_id": "09885703-...",
  "filename": "annual-report.pdf",
  "doc_type": "pdf",
  "sensitivity_tier": 1,
  "chunk_count": 137,
  "total_chars": 19837,
  "warnings": [],
  "parse_duration_ms": 94210,
  "extraction_method": "vision_v1"
}
```

You can also supply a stable `document_id` to re-ingest and replace an existing document atomically:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer <token>" \
  -F "file=@annual-report-v2.pdf" \
  -F "sensitivity_tier=1" \
  -F "document_id=09885703-..."
```

### Health check

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

## Running tests

```bash
uv run pytest tests/ -q
```

Tests use an in-memory SQLite database and an in-memory Qdrant instance. All LLM calls (vision parser, chunking, embedding) are mocked — no API keys needed to run the test suite.

## Document parsing pipeline

PDFs go through a vision pipeline:

1. **Render** — each page is rendered to a PNG at 1.5× resolution using PyMuPDF
2. **Extract** — pages are sent concurrently (max 3 at a time) to `qwen/qwen3-vl-32b-instruct` via OpenRouter with a prompt that instructs it to output clean markdown, preserve column order, render tables, and describe charts
3. **Chunk** — the full markdown is sent to DeepSeek in one call to produce semantically coherent chunks separated by `---`
4. **Embed** — chunks are sent to Voyage AI `voyage-3` (1024-dim) for embedding
5. **Store** — vectors and metadata are upserted into Qdrant; old chunks for the same `document_id` are removed after new ones are confirmed written

Non-PDF files (docx, xlsx, csv) skip the vision step and go directly to docling for parsing.

## Known limitations

- Chart data values are not reliably extracted if the numbers are not printed on the chart itself — the vision model describes the chart but cannot read pixel-level bar heights
- No query/retrieval endpoint yet — ingestion pipeline only
