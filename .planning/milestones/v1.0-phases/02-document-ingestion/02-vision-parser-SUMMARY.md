---
phase: "02"
plan: "vision-parser"
subsystem: document-ingestion
tags: [pdf-parsing, vision-llm, openrouter, pymupdf, refactor]
dependency-graph:
  requires: [02-01]
  provides: [vision-based PDF parsing]
  affects: [ingestion_service, document_parser, dependencies, ingest router]
tech-stack:
  added: [pymupdf>=1.27.0, qwen/qwen3-vl-32b-instruct via OpenRouter]
  patterns: [per-page vision LLM with semaphore concurrency control, lazy fitz import]
key-files:
  created:
    - backend/services/document_parser.py
  modified:
    - backend/services/ingestion_service.py
    - backend/core/dependencies.py
    - backend/main.py
    - backend/routers/ingest.py
    - tests/test_ingestion.py
    - pyproject.toml
decisions:
  - "PDF parsing: docling replaced by qwen3-vl-32b via OpenRouter (vision); docling retained for docx/xlsx/csv"
  - "embedding_client renamed openrouter_client throughout — single OpenRouter client now serves both vision parsing and future embedding calls"
  - "get_embedding_client() kept as backwards-compat alias in dependencies.py"
  - "extraction_method field updated from docling_v2 to vision_v1 for PDFs"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-06"
  tasks: 7
  files_changed: 7
---

# Phase 02 Vision Parser Refactor Summary

Replaced docling PDF parsing with a vision-LLM approach using `qwen/qwen3-vl-32b-instruct` via OpenRouter. Testing confirmed this model handles multi-column layouts, tables, and KPI callout boxes far better than docling on financial PDFs. Docling is retained only for non-PDF formats (docx, xlsx, csv) where it works correctly.

## What Changed

**New module: `backend/services/document_parser.py`**
- `parse_pdf_vision(file_path, client)` — renders each PDF page to a PNG via PyMuPDF (`fitz`), then calls the vision LLM concurrently (semaphore of 3) to extract markdown. Pages joined with `<!-- Page N -->` separators.
- `parse_docling(file_path)` — thin wrapper around docling for non-PDF formats.

**`backend/services/ingestion_service.py`**
- Removed `docling` import and `_parse_document` function.
- Parse block now branches: `pdf` → `parse_pdf_vision`, other → `parse_docling`.
- `embedding_client` parameter renamed `openrouter_client`.
- `extraction_method` field updated to `vision_v1` for PDFs.

**`backend/core/dependencies.py`**
- `_embedding_client` → `_openrouter_client` module-level singleton.
- `init_clients` signature updated.
- New `get_openrouter_client()` function.
- `get_embedding_client()` kept as backwards-compat alias.

**`backend/main.py`**
- Local variable `embedding_client` → `openrouter_client`.

**`backend/routers/ingest.py`**
- Imports `get_openrouter_client`, uses it as the dependency for the `openrouter_client` parameter.

**`pyproject.toml`**
- Added `pymupdf>=1.27.0`.

**`tests/test_ingestion.py`**
- Updated fixture to override `get_openrouter_client` instead of `get_embedding_client`.
- All `_parse_document` patches replaced with patches on both `parse_pdf_vision` (AsyncMock) and `parse_docling` (Mock) so both PDF and non-PDF code paths return mock markdown without running actual parsers.
- `_ingest_patches()` helper updated accordingly.

## Test Results

42 passed, 2 skipped — no regressions.

## Deviations from Plan

None — plan executed exactly as written. Note: `extraction_method` value changed from `docling_v2` to `vision_v1` for PDF records — this is consistent with the intent and was not explicitly specified in the plan, but is the correct value given the new parser.

## Self-Check: PASSED

- `backend/services/document_parser.py` exists and imports cleanly
- Commits e1a5062, bf2300d, d0c266e all present
- 42 tests pass
