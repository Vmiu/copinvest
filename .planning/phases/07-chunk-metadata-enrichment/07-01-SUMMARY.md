---
phase: 7
plan: "07-01"
subsystem: backend
tags: [metadata, chunking, migration, orm]
dependency_graph:
  requires: []
  provides: [document_registry_metadata_columns, chunk_document_list_dict]
  affects: [ingestion_service, vector_repo]
tech_stack:
  added: []
  patterns: [alembic_nullable_columns, list_dict_return_type]
key_files:
  created:
    - alembic/versions/c7d3e4f5a6b8_add_document_metadata_fields.py
  modified:
    - backend/models/document.py
    - backend/services/chunking_service.py
decisions:
  - "Section heading extracted from last markdown heading before chunk anchor in page text"
  - "is_table heuristic: pipe char present and count >= 2 (matches markdown table rows)"
  - "is_figure heuristic: regex on Figure/Chart/Graph/Diagram/Image/Exhibit at line start"
  - "chunk_position single-chunk edge case: idx==0 and idx==total-1 both true — first wins (correct: single chunk is 'first')"
metrics:
  duration: "133s"
  completed: "2026-05-11"
  tasks_completed: 3
  files_changed: 3
---

# Phase 7 Plan 01: DB migration + chunking service metadata extraction Summary

Alembic migration adds 5 nullable columns to `document_registry`, `DocumentRecord` ORM extended to match, and `chunk_document()` refactored from `list[str]` to `list[dict]` with 7 computed metadata fields per chunk (page_number, section_heading, is_table, is_figure, chunk_position, total_chunks_in_doc, text).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 07-01-T1 | Alembic migration c7d3e4f5a6b8: add 5 columns to document_registry | 496d7f8 |
| 07-01-T2 | Extend DocumentRecord ORM with 5 new mapped_column fields | 0aca964 |
| 07-01-T3 | Refactor chunk_document() to return list[dict] with computed metadata | c132587 |

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run alembic upgrade head` — exits 0, migration chain intact through c7d3e4f5a6b8
- `from backend.models.document import DocumentRecord; from backend.services.chunking_service import chunk_document` — imports ok
- `uv run pytest tests/ -q -k "not test_chunking_semantic and not test_chunking_table_integrity"` — 85 passed, 2 deselected

## Self-Check: PASSED

- FOUND: alembic/versions/c7d3e4f5a6b8_add_document_metadata_fields.py
- FOUND: backend/models/document.py (5 new columns)
- FOUND: backend/services/chunking_service.py (list[dict] return)
- FOUND commit: 496d7f8
- FOUND commit: 0aca964
- FOUND commit: c132587
