# Phase 2: Document Ingestion — Research

**Researched:** 2026-05-01
**Status:** Complete

## 1. Document Parsing with docling v2

### API Pattern
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("path/to/file.pdf")  # Also .docx, .xlsx
markdown = result.document.export_to_markdown()
```

### Key Facts
- `DocumentConverter` handles PDF, Word (.docx), and Excel (.xlsx/.csv) via a single API
- `export_to_markdown()` preserves table structure as markdown tables
- Tables are detected and exported as complete markdown table blocks — this aligns with D-03 (tables never split)
- For Excel/CSV: each sheet becomes a section, rows become markdown table rows with column headers
- docling is synchronous (CPU-bound parsing) — wrap in `asyncio.to_thread()` for FastAPI async endpoints
- Heavy dependency (~500MB with ML models for PDF layout detection). First import is slow; subsequent calls are fast
- Install: `uv pip install docling`

### Table Detection
- docling v2 uses a TableFormer model for PDF table detection
- Tables are exported as markdown tables with `|` delimiters
- The LLM chunking prompt can detect markdown table blocks and keep them intact

### Error Handling
- `ConversionError` raised on unparseable files
- Corrupt/password-protected PDFs raise exceptions — catch and return HTTP 422 per D-17

## 2. LLM-Based Semantic Chunking

### Implementation Pattern (D-01, D-02, D-04, D-07)
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

CHUNKING_SYSTEM_PROMPT = """You are a document chunking assistant. 
Split the following document into semantic chunks.
Rules:
- Each chunk should be a coherent unit of information
- NEVER split a markdown table across chunks
- Separate chunks with --- on its own line
- Preserve all content exactly — do not summarize or omit
- Each chunk should have a natural topic boundary
"""

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": CHUNKING_SYSTEM_PROMPT},
        {"role": "user", "content": document_markdown}
    ],
    temperature=0.0,
)
chunks = response.choices[0].message.content.split("\n---\n")
```

### Key Considerations
- gpt-4o-mini context window: 128K tokens — sufficient for most financial documents
- For very large documents (>100K tokens): need to pre-split into sections before LLM chunking
- Temperature 0.0 for deterministic chunking
- D-08: Retry logic — wrap in a retry loop (max 2 retries), fail document on 3rd failure
- Cost: gpt-4o-mini is ~$0.15/1M input tokens — very cheap for chunking

### Post-Processing
```python
chunks_text = response.choices[0].message.content.split("\n---\n")
chunks = [c.strip() for c in chunks_text if c.strip()]
```

## 3. OpenAI Embeddings (text-embedding-3-small)

### Async Batch Embedding Pattern
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

response = await client.embeddings.create(
    model="text-embedding-3-small",
    input=["chunk 1 text", "chunk 2 text", ...],  # batch up to 2048 texts
)
vectors = [item.embedding for item in response.data]
```

### Key Facts
- text-embedding-3-small: 1536 dimensions (matches existing Qdrant collection from Phase 1)
- Max input: 8191 tokens per text
- Batch: up to 2048 texts per API call
- Cost: $0.02 per 1M tokens
- AsyncOpenAI for non-blocking calls in FastAPI
- Settings needs `openai_api_key: str` added to config.py

## 4. Qdrant Upsert and Delete Operations

### Upsert Points with Metadata (D-05)
```python
from qdrant_client.models import PointStruct
import uuid

points = [
    PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding_vector,
        payload={
            "source_id": document_id,
            "doc_type": "pdf",
            "sensitivity_tier": 3,
            "allowed_roles": ["compliance", "senior_adviser"],
            "chunk_index": i,
            "section_title": "Financial Summary",
            "text": chunk_text,
        }
    )
    for i, (chunk_text, embedding_vector) in enumerate(zip(chunks, vectors))
]

client.upsert(
    collection_name=settings.qdrant_collection,
    points=points,
)
```

### Delete by Source ID for Re-ingestion (D-12)
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

client.delete(
    collection_name=settings.qdrant_collection,
    points_selector=Filter(
        must=[
            FieldCondition(
                key="source_id",
                match=MatchValue(value=document_id),
            )
        ]
    ),
)
```

### Key Facts
- `source_id` needs a payload index for efficient deletion — add to `setup_collection()`
- `allowed_roles` mapping from SensitivityTier:
  - Public (1): ["adviser", "senior_adviser", "compliance"]
  - Internal (2): ["senior_adviser", "compliance"]
  - Restricted (3): ["senior_adviser", "compliance"]
  - Confidential (4): ["compliance"]
- This mapping already exists conceptually in Phase 1 RBAC design (D-05 from Phase 1 context)

## 5. FastAPI File Upload Endpoint

### Pattern (D-09, D-10, D-11)
```python
from fastapi import APIRouter, UploadFile, File, Form, Depends

router = APIRouter(prefix="/api/v1", tags=["ingest"])

@router.post("/ingest", status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    sensitivity_tier: SensitivityTier = Form(...),
    document_id: str | None = Form(None),
    current_user: User = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
):
    ...
```

### Key Facts
- `python-multipart` already in dependencies (required for Form/File)
- Need a `require_role()` dependency that wraps `get_current_user` and checks role
- UploadFile provides `.filename`, `.content_type`, `.read()` (async)
- File needs to be saved to temp location for docling (it reads from filesystem)
- Use `tempfile.NamedTemporaryFile` for transient storage during processing

## 6. Document Registry Model

### SQLAlchemy Model (D-16)
```python
class DocumentRecord(Base):
    __tablename__ = "document_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(50))
    sensitivity_tier: Mapped[int] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer)
    char_count: Mapped[int] = mapped_column(Integer)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    parse_duration_ms: Mapped[int] = mapped_column(Integer)
    extraction_method: Mapped[str] = mapped_column(String(100))
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ingested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
```

### Key Facts
- Needs Alembic migration
- `document_id` is unique — re-ingestion updates the existing record (D-12)
- `warnings` stored as JSON string (list of warning messages)
- `extraction_method` = "docling_v2" (for future-proofing if parser changes)

## 7. Integration with Existing Phase 1 Code

### Files to Modify
- `backend/core/config.py` — Add `openai_api_key: str` to Settings
- `backend/repositories/vector_repo.py` — Add `upsert_points()` and `delete_by_source()` functions, add `source_id` payload index to `setup_collection()`
- `backend/models/__init__.py` — Export new DocumentRecord model

### New Files to Create
- `backend/models/document.py` — DocumentRecord SQLAlchemy model
- `backend/services/ingestion_service.py` — Orchestrates: parse → chunk → embed → store pipeline
- `backend/services/chunking_service.py` — LLM chunking logic with retry
- `backend/services/embedding_service.py` — OpenAI embedding calls
- `backend/routers/ingest.py` — POST /api/v1/ingest endpoint
- `backend/schemas/ingest.py` — Pydantic response models
- `backend/repositories/document_repo.py` — Document registry CRUD
- `alembic/versions/xxx_add_document_registry.py` — Migration
- `tests/test_ingestion.py` — Integration tests

### Dependency Additions (pyproject.toml)
```
"docling>=2.12.0",
"openai>=1.68.0",
```

## 8. Validation Architecture

### Test Strategy
- **Unit tests**: Chunking post-processing (split by ---), metadata mapping (tier → allowed_roles)
- **Integration tests**: Full pipeline with mock OpenAI (mock LLM chunking response, mock embeddings)
- **Qdrant tests**: Use qdrant-client's in-memory mode (`:memory:`) for upsert/delete verification
- **API tests**: httpx TestClient for endpoint auth, file upload, error responses

### Key Test Scenarios
1. PDF with tables → verify table chunks are intact
2. Word doc → verify text extraction
3. Excel/CSV → verify column headers preserved
4. Re-ingestion → verify old chunks deleted, new chunks stored
5. Non-compliance role → verify 403
6. Corrupt file → verify 422
7. LLM failure after retries → verify document fails entirely

## RESEARCH COMPLETE
