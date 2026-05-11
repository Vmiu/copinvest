---
phase: 7
plan: "07-02"
subsystem: backend
tags: [metadata, vector-repo, ingestion, schemas, filters]
dependency_graph:
  requires: [document_registry_metadata_columns, chunk_document_list_dict]
  provides: [upsert_chunks_metadata_param, ingest_metadata_pipeline, document_list_filters]
  affects: [vector_repo, ingestion_service, ingest_router, document_repo, document_schemas, documents_router]
tech_stack:
  added: []
  patterns: [payload_merge_spread, dict_based_model_validate, form_field_extension]
key_files:
  modified:
    - backend/repositories/vector_repo.py
    - backend/services/ingestion_service.py
    - backend/routers/ingest.py
    - backend/repositories/document_repo.py
    - backend/schemas/document.py
    - backend/routers/documents.py
    - tests/test_ingestion.py
decisions:
  - "product_codes JSON parse done at read time in router via dict-based model_validate to avoid None→list[str] Pydantic coercion failure on existing rows"
  - "model_validate called with dict (column key/value pairs) rather than ORM object to allow product_codes override before validation"
metrics:
  duration: "391s"
  completed: "2026-05-11"
  tasks_completed: 4
  files_changed: 7
---

# Phase 7 Plan 02: Ingestion service + vector repo wiring Summary

End-to-end metadata wiring: upsert_chunks accepts per-chunk metadata dicts merged into Qdrant payloads; ingest_document passes 5 doc-level fields through payload_base and DocumentRecord; POST /ingest accepts document_type, language, jurisdiction (required), product_codes, parent_doc_title; GET /documents filters by document_type and jurisdiction with product_codes JSON-parsed on read.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 07-02-T1 | Add 3 Qdrant payload indexes; extend upsert_chunks with chunk_metadata param | 4e703df |
| 07-02-T2 | Wire 5 doc-level metadata fields through ingest_document pipeline | e8b85d7 |
| 07-02-T3 | Add 5 new Form fields to POST /ingest router | f48fdcd |
| 07-02-T4 | Extend DocumentListItem schema, list_documents filters, GET /documents query params | 48297f4 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] product_codes None→list[str] Pydantic validation failure**
- **Found during:** Task 4 (test run)
- **Issue:** `DocumentListItem.model_validate(d)` failed with `Input should be a valid list` when `d.product_codes` is `None` (existing rows). The `from_attributes=True` mode passes the raw `None` to the `list[str]` field before the post-validate JSON parse could run.
- **Fix:** Build a plain dict from ORM column values and override `product_codes` before calling `model_validate`, bypassing the ORM attribute coercion path entirely.
- **Files modified:** backend/routers/documents.py
- **Commit:** 48297f4

**2. [Rule 1 - Bug] Ingestion tests broken by list[dict] chunk format and required form fields**
- **Found during:** Task 4 (full test suite run)
- **Issue:** `_MOCK_CHUNKS` was `list[str]`; service now does `c["text"]` on each chunk. All POST /ingest test calls lacked the 3 new required form fields.
- **Fix:** Updated `_MOCK_CHUNKS` to `list[dict]`, added `_INGEST_META` constant, updated all test POST calls and the `total_chars` assertion.
- **Files modified:** tests/test_ingestion.py
- **Commit:** 1b93de5

## Verification

- All imports ok: `from backend.repositories.vector_repo import upsert_chunks, setup_collection; from backend.services.ingestion_service import ingest_document; from backend.schemas.document import DocumentListItem` — exits 0
- `uv run pytest tests/ -q` — 85 passed, 2 skipped

## Self-Check: PASSED

- FOUND: backend/repositories/vector_repo.py (field_name="document_type", field_name="is_table", field_name="is_figure", chunk_metadata param)
- FOUND: backend/services/ingestion_service.py (document_type param, chunk_texts extraction, payload_base extension, chunk_metadata=chunk_meta)
- FOUND: backend/routers/ingest.py (document_type Form, language Form, jurisdiction Form, codes parsing)
- FOUND: backend/schemas/document.py (document_type, product_codes, parent_doc_title fields)
- FOUND: backend/repositories/document_repo.py (document_type filter, jurisdiction filter)
- FOUND: backend/routers/documents.py (Query params, product_codes JSON parse)
- FOUND commit: 4e703df
- FOUND commit: e8b85d7
- FOUND commit: f48fdcd
- FOUND commit: 48297f4
- FOUND commit: 1b93de5
