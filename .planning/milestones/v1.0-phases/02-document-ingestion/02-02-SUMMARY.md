---
phase: 02-document-ingestion
plan: "02"
subsystem: api
tags: [openai, gpt-4o-mini, text-embedding-3-small, chunking, embeddings, rag]

requires:
  - phase: 02-document-ingestion/02-01
    provides: openai_api_key in Settings, AsyncOpenAI client pattern, upsert_chunks interface

provides:
  - chunking_service.chunk_document(markdown, client) — LLM-based semantic chunking via gpt-4o-mini
  - embedding_service.embed_chunks(chunks, client) — batch embeddings via text-embedding-3-small
  - openai>=1.68.0 added to pyproject.toml dependencies

affects: [02-03-parser, 02-04-ingestion-service]

tech-stack:
  added:
    - "openai>=1.68.0"
  patterns:
    - "Client injection: AsyncOpenAI passed as parameter, never constructed inside service module"
    - "Retry loop: for attempt in range(MAX_ATTEMPTS) with try/except, raise RuntimeError after exhausting attempts"
    - "Split by \\n---\\n: LLM separator parsing strips empty chunks via list comprehension"

key-files:
  created:
    - backend/services/chunking_service.py
    - backend/services/embedding_service.py
  modified:
    - pyproject.toml

key-decisions:
  - "AsyncOpenAI client injected as parameter — no get_settings() in service modules (D-01, testability)"
  - "MAX_ATTEMPTS=3: retry up to 2 times then raise RuntimeError (D-08)"
  - "temperature=0.0 for deterministic chunking output (D-01)"

patterns-established:
  - "Service modules use injected clients — no internal get_settings() calls in chunking/embedding services"

requirements-completed: [INGEST-06, INGEST-07]

duration: 5min
completed: "2026-05-06"
---

# Phase 2 Plan 02: Chunking and Embedding Services Summary

**gpt-4o-mini semantic chunker with table-integrity enforcement and text-embedding-3-small batch embedder, both using injected AsyncOpenAI clients**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-06T11:32:00Z
- **Completed:** 2026-05-06T11:37:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `chunk_document(markdown, client)` sends parsed markdown to gpt-4o-mini with a system prompt that enforces table integrity (NEVER split a markdown table) and uses `---` separators
- 3-attempt retry loop with `structlog` warnings on each failure; raises `RuntimeError` after exhausting attempts (D-08)
- `embed_chunks(chunks, client)` batches all chunks in a single `client.embeddings.create()` call returning `list[list[float]]` matching Qdrant's 1536-dim vector format
- `openai>=1.68.0` added to `pyproject.toml` — was missing from dependencies (required by both service modules)

## Task Commits

1. **Task 1: Create chunking_service.py** - `c9d2b67` (feat)
2. **Task 2: Create embedding_service.py** - `9a71f4a` (feat)

**Plan metadata:** *(this commit)*

## Files Created/Modified
- `backend/services/chunking_service.py` — LLM chunker: CHUNKING_PROMPT, MAX_ATTEMPTS=3, chunk_document()
- `backend/services/embedding_service.py` — Batch embedder: text-embedding-3-small, embed_chunks()
- `pyproject.toml` — Added openai>=1.68.0 to core dependencies

## Decisions Made
- AsyncOpenAI client injected as parameter in both services — matches the plan's stated design decision for testability; no `get_settings()` import in either service module
- `openai>=1.68.0` pinned per CLAUDE.md tech stack specification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added openai>=1.68.0 to pyproject.toml**
- **Found during:** Task 1 (chunking_service.py import verification)
- **Issue:** `from openai import AsyncOpenAI` raised `ModuleNotFoundError: No module named 'openai'` — package missing from pyproject.toml despite being required by both new service files
- **Fix:** Added `"openai>=1.68.0"` to `[project] dependencies` in pyproject.toml; ran `uv pip install -e ".[dev]"` to install (openai==2.34.0 resolved)
- **Files modified:** `pyproject.toml`
- **Verification:** `uv run python -c "from backend.services.chunking_service import chunk_document"` exits 0; all 31 tests still pass
- **Committed in:** `c9d2b67` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for correct operation — openai is the core dependency for both services. No scope creep.

## Issues Encountered
- None beyond the deviation documented above.

## User Setup Required
None — openai_api_key is already set in `.env` (placeholder added in Plan 02-01). Real key required for production ingestion.

## Next Phase Readiness
- `chunk_document(markdown, client)` ready for Plan 02-03 (parser service) to call after docling parsing
- `embed_chunks(chunks, client)` ready for Plan 02-04 (ingestion service orchestration) to call after chunking
- Both services accept injected `AsyncOpenAI` clients — test fixtures can pass `AsyncMock` without patching modules

---
*Phase: 02-document-ingestion*
*Completed: 2026-05-06*

## Self-Check: PASSED

- FOUND: backend/services/chunking_service.py
- FOUND: backend/services/embedding_service.py
- FOUND: .planning/phases/02-document-ingestion/02-02-SUMMARY.md
- FOUND: c9d2b67 (Task 1 commit)
- FOUND: 9a71f4a (Task 2 commit)

