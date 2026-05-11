# Phase 7: Chunk Metadata Enrichment — Research

**Phase:** 7 — Chunk Metadata Enrichment
**Requirement:** META-01
**Date:** 2026-05-11

---

## Summary

Phase 7 adds 11 metadata fields to every Qdrant chunk payload, extends the `document_registry` DB table, and re-ingests all documents. The codebase is well-structured for this change: the ingestion pipeline has clear seams where new fields slot in, and the write-then-replace atomicity pattern already handles safe re-ingestion.

---

## 1. Metadata Field Sourcing

### Caller-supplied (at upload time via form/API)
| Field | Type | Source |
|-------|------|--------|
| `document_type` | str | Form field — one of: `factsheet`, `compliance_doc`, `meeting_template`, `research_report`, `other` |
| `language` | str | Form field — e.g. `en`, `zh` |
| `jurisdiction` | str | Form field — e.g. `HK`, `SG`, `global` |
| `product_codes` | list[str] | Form field — comma-separated string, parsed to list |
| `parent_doc_title` | str | Form field — human-readable display name |

### Computed during chunking (no LLM calls)
| Field | Type | Extraction method |
|-------|------|-------------------|
| `page_number` | int | Page index from `_split_pages()` — thread page index through `_chunk_page()` |
| `section_heading` | str | Last `#`/`##`/`###` heading seen before the chunk in the page markdown |
| `is_table` | bool | Chunk text contains `\|` (markdown table pattern) |
| `is_figure` | bool | Chunk text contains figure description keywords from vision prompt output |

### Computed post-chunking (before upsert)
| Field | Type | Extraction method |
|-------|------|-------------------|
| `chunk_position` | str | `first` / `middle` / `last` based on index in flat chunk list |
| `total_chunks_in_doc` | int | `len(chunks)` after all pages are chunked |

---

## 2. Code Change Map

### `backend/services/chunking_service.py`

**Current:** `chunk_document()` returns `list[str]`

**Change:** Return `list[dict]` where each dict has `text` + computed metadata fields:
```python
{"text": str, "page_number": int, "section_heading": str, "is_table": bool, "is_figure": bool}
```

- `_split_pages()` — unchanged; already splits on `<!-- Page N -->` markers
- `_chunk_page()` — add `page_num: int` parameter; extract `section_heading` and `is_table`/`is_figure` from each chunk text before returning
- `chunk_document()` — pass page index to `_chunk_page()`; after gathering results, add `chunk_position` and `total_chunks_in_doc` to each dict

**Section heading extraction:**
```python
import re
_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)', re.MULTILINE)

def _extract_section_heading(page_text: str, chunk_text: str) -> str:
    # Find last heading in page_text that appears before chunk_text
    headings = _HEADING_RE.findall(page_text[:page_text.find(chunk_text[:50])])
    return headings[-1] if headings else ""
```

**is_figure detection:** Vision prompt outputs phrases like "Figure:", "Chart:", "Graph:" — check for these prefixes.

### `backend/services/ingestion_service.py`

**Current:** `ingest_document()` takes no doc-level metadata params; `payload_base` has 4 fields.

**Change:**
1. Add 5 new parameters: `document_type`, `language`, `jurisdiction`, `product_codes: list[str]`, `parent_doc_title`
2. `chunk_document()` now returns `list[dict]` — extract `texts` and `chunk_metadata` lists
3. Extend `payload_base` with the 5 caller-supplied fields
4. In `upsert_chunks()`, merge `chunk_metadata[i]` into each point's payload alongside `payload_base`
5. Pass new fields to `DocumentRecord` constructor

### `backend/repositories/vector_repo.py`

**`upsert_chunks()` signature change:**
```python
def upsert_chunks(
    client, chunks: list[str], vectors, payload_base: dict,
    chunk_metadata: list[dict] | None = None, collection=None
) -> tuple[int, list[str]]:
```
Each point payload: `{**payload_base, "chunk_index": i, "text": chunk, **(chunk_metadata[i] if chunk_metadata else {})}`

**`setup_collection()` — add 3 new indexes:**
```python
client.create_payload_index(name, "document_type", PayloadSchemaType.KEYWORD)
client.create_payload_index(name, "is_table", PayloadSchemaType.BOOL)
client.create_payload_index(name, "is_figure", PayloadSchemaType.BOOL)
```

### `backend/models/document.py`

Add 5 new columns to `DocumentRecord`:
```python
document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
language: Mapped[str | None] = mapped_column(String(10), nullable=True)
jurisdiction: Mapped[str | None] = mapped_column(String(50), nullable=True)
product_codes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
parent_doc_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

Nullable to preserve backward compatibility with existing records.

### `backend/schemas/document.py`

Extend `DocumentListItem` with the 5 new optional fields. Add `document_type` and `jurisdiction` as filter params to the list endpoint.

### `backend/routers/ingest.py`

Add 5 new `Form(...)` parameters (document_type required, others optional). Pass through to `ingestion_service.ingest_document()`.

### Alembic migration

New migration (depends on `b9c4d2e1f3a7`): add 5 columns to `document_registry`. All nullable — no data migration needed for existing rows.

### Frontend: `IngestDocument.tsx`

Add 5 new form fields per UI-SPEC: Document Type (Select, required), Language (Select, required), Jurisdiction (Select, required), Product Codes (text input, optional), Display Title (text input, optional). All receive `disabled={loading}`.

### Frontend: `DocumentRegistry.tsx`

Add 2 new filter Selects: Document Type (`w-44`) and Jurisdiction (`w-36`). Filter logic mirrors existing `tierFilter` pattern. Add `document_type` and `jurisdiction` columns to the table.

### Frontend: `frontend/src/types/api.ts`

Extend `DocumentListItem` type with 5 new optional fields.

### Frontend: `frontend/src/api/documents.ts`

Pass `document_type` and `jurisdiction` as query params to the list endpoint.

---

## 3. Re-ingestion Strategy

**Trigger:** Admin-initiated via a new `POST /api/v1/admin/reingest-all` endpoint (or standalone script).

**Safety:** Existing `delete_by_source_except_new()` write-then-replace pattern already handles atomicity — new chunks are written before old ones are deleted. Running twice produces the same payload (idempotent).

**Scope:** Re-ingest all documents in `document_registry`. For existing records without the new doc-level fields, use sensible defaults (`document_type="other"`, `language="en"`, `jurisdiction="global"`, `product_codes=[]`, `parent_doc_title=filename`).

---

## 4. Qdrant Index Strategy

Per D-06/D-07:
- **Index:** `document_type` (KEYWORD), `is_table` (BOOL), `is_figure` (BOOL)
- **No index:** `jurisdiction`, `language` — filtered at DB layer via `document_registry`

`setup_collection()` is idempotent — safe to call on existing collection.

---

## 5. Test Strategy

### Unit tests (new file: `tests/test_chunking_metadata.py`)
- `_chunk_page()` returns dicts with correct `page_number`, `section_heading`, `is_table`, `is_figure`
- `chunk_document()` sets `chunk_position` correctly for first/middle/last
- `chunk_document()` sets `total_chunks_in_doc` = total chunk count

### Integration tests (extend `tests/test_ingestion.py`)
- POST `/ingest` with new fields → Qdrant point payload contains all 11 fields
- POST `/ingest` twice with same `document_id` → same chunk count, no duplicates (idempotency)
- GET `/documents` with `document_type` filter → returns only matching records

---

## 6. Risk & Mitigations

| Risk | Mitigation |
|------|-----------|
| `chunk_document()` return type change breaks callers | Only one caller: `ingestion_service.py`. Update together. |
| Section heading extraction misses headings in non-PDF docs | Default to `""` — non-blocking, field is informational |
| Re-ingest of large corpus is slow | Existing `MAX_CONCURRENT=5` semaphore limits parallel LLM calls; acceptable for admin-triggered operation |
| Existing Qdrant points lack new fields | Phase 8 agent skills must handle missing fields gracefully (use `.get()` with defaults) |

---

## RESEARCH COMPLETE

Phase 7 is well-scoped. The main seam is `chunk_document()` return type: `list[str]` → `list[dict]`. All other changes flow from that. No new dependencies required.
