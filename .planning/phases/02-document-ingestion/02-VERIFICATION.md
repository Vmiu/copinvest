---
phase: 02-document-ingestion
verified: 2026-05-06T22:00:00Z
status: human_needed
score: 4/5
overrides_applied: 0
human_verification:
  - test: "Ingest a PDF containing a markdown table, then inspect the Qdrant points to confirm the table was kept as a single complete chunk (not split across two points)"
    expected: "Each Qdrant point retrieved for the document should contain either the whole table or no portion of it — no point should contain a partial table row"
    why_human: "Table integrity (INGEST-07) is enforced via LLM system prompt only. The two unit test stubs (test_chunking_semantic, test_chunking_table_integrity) remain as skipped stubs — they were never implemented despite the plan claiming INGEST-06/07 as complete. Verifying prompt-level LLM behavioral guarantees requires a live API call with a real table document."
---

# Phase 2: Document Ingestion Verification Report

**Phase Goal:** Build the document ingestion pipeline — parse, chunk, embed, and store documents with sensitivity-tier RBAC metadata so advisers can query approved content in Phase 3.
**Verified:** 2026-05-06T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (from ROADMAP Success Criteria) | Status | Evidence |
|---|---------------------------------------|--------|----------|
| 1 | Admin can ingest PDF/Word/Excel and extracted text preserves table structure/formatting/column headers | VERIFIED | `ingestion_service.py` uses docling `DocumentConverter` for all three formats. `DOC_TYPE_MAP` covers .pdf, .docx, .doc, .xlsx, .xls, .csv. Tests `test_ingest_pdf_success`, `test_ingest_docx_success`, `test_ingest_csv_success` all pass (201, correct doc_type). Table structure preservation is delegated to docling's markdown export. |
| 2 | Admin can assign a sensitivity tier (Public/Internal/Restricted/Confidential) at ingestion time; non-compliance users are rejected | VERIFIED | `require_role("compliance")` on POST /api/v1/ingest. `SensitivityTier = Form(...)` validates enum values at FastAPI layer. `test_ingest_requires_compliance_role` confirms 403 for adviser role. `test_ingest_sensitivity_tier_stored` confirms tier stored in Qdrant point payload. |
| 3 | Each chunk in Qdrant carries source_id, doc_type, sensitivity_tier, and allowed_roles metadata | VERIFIED | `payload_base` in `ingestion_service.py` (lines 87-92) includes all four fields plus chunk_index and text. `TIER_TO_ROLES` maps all 4 tiers to correct role lists. `test_ingest_chunks_have_metadata` asserts `{"source_id", "doc_type", "sensitivity_tier", "allowed_roles", "chunk_index", "text"}` are present on every Qdrant point. PASSES. |
| 4 | Financial tables are stored as complete chunks — no table split across chunk boundaries | UNCERTAIN | Enforcement is purely in the LLM system prompt: `CHUNKING_PROMPT` contains "NEVER split a markdown table across chunks". The enforcement mechanism EXISTS in `chunking_service.py` line 13. However, `test_chunking_table_integrity` is a skipped stub (`@pytest.mark.skip`). No automated test verifies this behavior with a real table document. Needs human verification with live LLM call. |
| 5 | Ingestion produces a log entry per document with character count, warnings, and extraction method | VERIFIED | `DocumentRecord` model has chunk_count, total_chars, warnings (Text, nullable), parse_duration_ms, extraction_method. `ingest_document()` populates all fields and persists via `document_repo.upsert_document_record`. `test_ingest_quality_metrics` asserts chunk_count, total_chars, parse_duration_ms >= 0 in 201 response. PASSES. |

**Score:** 4/5 truths verified (1 UNCERTAIN — needs human verification)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/models/document.py` | DocumentRecord model with document_registry table | VERIFIED | 26 lines. `DocumentRecord(Base)`, `__tablename__="document_registry"`, all 12 columns including document_id (unique+indexed), sensitivity_tier, ingested_by (FK to users.id). |
| `alembic/versions/23b31f0ac9b4_add_document_registry.py` | Migration creating document_registry | VERIFIED | Auto-generated. `op.create_table('document_registry', ...)` with all columns, `sa.ForeignKeyConstraint(['ingested_by'], ['users.id'])`, unique index on document_id. |
| `backend/repositories/document_repo.py` | Async CRUD for DocumentRecord | VERIFIED | 31 lines. `get_document_by_id` and `upsert_document_record`. Bug fix applied: `ingested_at` not overwritten on update path (preserves original timestamp). |
| `backend/repositories/vector_repo.py` | upsert_chunks + delete_by_source | VERIFIED | 145 lines. `upsert_chunks` with UUID point IDs and payload spread. `delete_by_source` with Filter(must=[FieldCondition(source_id)]). `get_qdrant_client()` factory. `source_id` payload index in `setup_collection()`. |
| `backend/schemas/ingest.py` | IngestResponse Pydantic schema | VERIFIED | 13 lines. `IngestResponse(BaseModel)` with all 9 response fields including warnings: list[str]. |
| `backend/core/config.py` | openai_api_key in Settings | VERIFIED | Line 12: `openai_api_key: str` — no default, forces explicit env config (T-02-05). |
| `backend/core/dependencies.py` | require_role dependency factory | VERIFIED | Lines 48-56. `require_role(*allowed_roles)` factory wrapping `get_current_user` with HTTP 403. Also contains `init_clients`, `get_openai_client`, `get_qdrant_client` for application-lifetime singletons. |
| `backend/services/chunking_service.py` | LLM semantic chunking via gpt-4o-mini | VERIFIED | 50 lines. `CHUNKING_PROMPT` with table integrity instruction. `chunk_document(markdown, client)`. `MAX_ATTEMPTS=3`, `temperature=0.0`. Uses `re.split(r'\n?^---$\n?', ...)` (upgrade from plan's `"\n---\n"` to handle varied LLM output). |
| `backend/services/embedding_service.py` | Batch embeddings via text-embedding-3-small | VERIFIED | 16 lines. `embed_chunks(chunks, client)`. model="text-embedding-3-small". Single batch call. Returns `[item.embedding for item in response.data]`. |
| `backend/services/ingestion_service.py` | Full parse→chunk→embed→store→record pipeline | VERIFIED | 128 lines. `ingest_document(db, file_content, filename, sensitivity_tier, user_id, openai_client, qdrant_client)`. Uses `asyncio.to_thread(_parse_document)`. Atomicity improvement: write-then-replace via `delete_by_source_except_new` (stronger than plan's pre-delete). |
| `backend/routers/ingest.py` | POST /api/v1/ingest endpoint | VERIFIED | 56 lines. `require_role("compliance")`, File + SensitivityTier Form + optional document_id Form. ValueError/RuntimeError → 422. 50MB upload limit added (improvement over plan). user_id from `current_user["user_id"]` (correct — matches get_current_user return shape). |
| `backend/main.py` | ingest router registered | VERIFIED | Line 13: `from backend.routers.ingest import router as ingest_router`. Line 45: `app.include_router(ingest_router)`. Lifespan initializes OpenAI + Qdrant clients via `init_clients()`. |
| `tests/test_ingestion.py` | 11 integration tests | VERIFIED | 530 lines. All 11 tests present and passing: pdf_success, docx_success, csv_success, requires_compliance_role, sensitivity_tier_stored, chunks_have_metadata, reingest_replaces_chunks, document_id_optional, quality_metrics, unsupported_file_type, empty_file. |
| `tests/test_chunking.py` | Chunking tests for INGEST-06/07 | STUB | 13 lines. Both `test_chunking_semantic` and `test_chunking_table_integrity` are `@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 02-04")`. Plan 02-04 claimed INGEST-06/07 completed but did not fill in these stubs. The skip reason still points to Plan 02-04 as future work that was never executed. |
| `pyproject.toml` | docling and openai dependencies | VERIFIED | Contains `"docling>=2.12.0"` and `"openai>=1.68.0"` in dependencies. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/main.py` | `backend/routers/ingest.py` | `app.include_router(ingest_router)` | WIRED | Line 13 import, line 45 registration. |
| `backend/routers/ingest.py` | `backend/services/ingestion_service.py` | `ingestion_service.ingest_document()` | WIRED | Line 11 import, line 40 `await ingestion_service.ingest_document(...)` with all params. |
| `backend/routers/ingest.py` | `backend/core/dependencies.py` | `require_role("compliance")`, `get_openai_client`, `get_qdrant_client` | WIRED | Line 8 imports, lines 25/27/28 Depends() injections. |
| `backend/main.py` | `backend/core/dependencies.py` | `init_clients(openai_client, qdrant_client)` | WIRED | Line 9 import, line 27 `init_clients(openai_client, qdrant_client)` in lifespan. |
| `backend/services/ingestion_service.py` | `backend/services/chunking_service.py` | `chunking_service.chunk_document(markdown, openai_client)` | WIRED | Line 17 import, line 80 call. |
| `backend/services/ingestion_service.py` | `backend/services/embedding_service.py` | `embedding_service.embed_chunks(chunks, openai_client)` | WIRED | Line 17 import, line 83 call. |
| `backend/services/ingestion_service.py` | `backend/repositories/vector_repo.py` | `vector_repo.upsert_chunks`, `vector_repo.delete_by_source_except_new` | WIRED | Line 16 import, lines 93/96 calls. |
| `backend/services/ingestion_service.py` | `backend/repositories/document_repo.py` | `document_repo.upsert_document_record(db, record)` | WIRED | Line 16 import, line 114 call. |
| `backend/repositories/vector_repo.py` | `backend/core/config.py` | `get_settings()` for qdrant host/port/collection | WIRED | Line 14 import, used in `get_qdrant_client()`, `setup_collection()`, `upsert_chunks()`, `delete_by_source()`. |
| `backend/models/__init__.py` | `backend/models/document.py` | `from backend.models.document import DocumentRecord` | WIRED | Line 4 of __init__.py. |

### Data-Flow Trace (Level 4)

Not applicable. Phase 2 builds a write pipeline (ingest → store), not a render pipeline. No component renders dynamic data to a UI. Phase 3 (RAG Query) will consume these chunks; Phase 5 (Web UI) will render the document registry. Data flows from those phases will be verified in their respective verifications.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All services importable | `uv run python -c "from backend.services.ingestion_service import ingest_document; from backend.services.chunking_service import chunk_document; from backend.services.embedding_service import embed_chunks; print('OK')"` | All services importable: OK | PASS |
| Full test suite (42 passed, 2 skipped) | `SECRET_KEY=testsecret OPENAI_API_KEY=test-placeholder uv run pytest tests/ -q` | 42 passed, 2 skipped in 6.21s | PASS |
| All 11 ingestion tests | `SECRET_KEY=testsecret OPENAI_API_KEY=test-placeholder uv run pytest tests/test_ingestion.py -v` | 11/11 PASSED | PASS |
| All 15 phase commits exist in git | `git log --oneline \| grep -E "943f03a\|c314f00\|d14807c\|..."` | All 15 commit hashes found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INGEST-01 | 02-03, 02-04 | System can parse PDF documents with table structure preserved | SATISFIED | `_parse_document` uses docling `DocumentConverter`. `test_ingest_pdf_success` passes (201, doc_type=pdf). |
| INGEST-02 | 02-03, 02-04 | System can parse Word (.docx) with formatting preserved | SATISFIED | `.docx` in `DOC_TYPE_MAP`. `test_ingest_docx_success` passes (201, doc_type=docx). |
| INGEST-03 | 02-03, 02-04 | System can parse Excel/CSV with column headers preserved | SATISFIED | `.xlsx`, `.xls`, `.csv` in `DOC_TYPE_MAP`. `test_ingest_csv_success` passes (201, doc_type=csv). |
| INGEST-04 | 02-01, 02-04 | Admin can assign sensitivity tier at ingestion time | SATISFIED | `SensitivityTier = Form(...)` + `require_role("compliance")`. Tests confirm 403 for adviser, tier stored in payload. |
| INGEST-05 | 02-01, 02-04 | Each chunk tagged with source_id, doc_type, sensitivity_tier, allowed_roles | SATISFIED | `payload_base` dict with all 4 fields + chunk_index and text. `test_ingest_chunks_have_metadata` asserts all 6 keys present on every Qdrant point. |
| INGEST-06 | 02-02 | Documents chunked using semantic/structural boundaries (not fixed token counts) | SATISFIED (impl) / NEEDS HUMAN (test) | Chunking uses gpt-4o-mini with semantic instruction prompt. No fixed-token logic in codebase. `test_chunking_semantic` exists but is skipped stub — semantic quality of LLM output requires live verification. |
| INGEST-07 | 02-02 | Financial tables kept as complete units during chunking | SATISFIED (impl) / NEEDS HUMAN (test) | CHUNKING_PROMPT line 13: "NEVER split a markdown table across chunks". `test_chunking_table_integrity` exists but is skipped stub — prompt enforcement requires live LLM call with table document to confirm. |
| INGEST-08 | 02-01, 02-04 | Ingestion logs parsing quality metrics per document | SATISFIED | `DocumentRecord` stores chunk_count, total_chars, warnings, parse_duration_ms, extraction_method. `test_ingest_quality_metrics` asserts all in 201 response. |

No orphaned requirements. All 8 INGEST IDs claimed by phase plans are accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_chunking.py` | 4, 10 | `@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 02-04")` | Warning | INGEST-06 and INGEST-07 test stubs were never replaced with real tests. Plan 02-04 SUMMARY claimed these requirements as "completed" but the stubs remain skipped. The implementation (chunking prompt) is present; only test coverage is absent. |

No TODOs, FIXMEs, empty implementations, or placeholder returns found in any production code file.

### Human Verification Required

### 1. Table Integrity (INGEST-07 / SC-4)

**Test:** Create a small PDF or Word document containing a markdown-style table (e.g., a fund fact sheet with a 3-column holdings table). Ingest it via `POST /api/v1/ingest` with a real OPENAI_API_KEY. Then scroll Qdrant for the document's source_id and inspect the payload `text` field of each point.

**Expected:** Each Qdrant point's `text` contains either the complete table (all rows and the header) or no portion of the table. No point should contain partial rows (e.g., only the header row or only some data rows separated from others).

**Why human:** Table integrity is enforced via the LLM system prompt (`CHUNKING_PROMPT`). The `test_chunking_table_integrity` test is a skipped stub — no automated test ever confirmed this behavior with a real document. Verifying LLM prompt adherence requires a live API call and manual inspection of the resulting chunk payload.

### Gaps Summary

No structural gaps block the phase goal. The ingestion pipeline is fully implemented: parse (docling) → chunk (gpt-4o-mini) → embed (text-embedding-3-small) → store (Qdrant with RBAC metadata) → record (DocumentRecord in SQLite). All 11 integration tests pass. All 15 phase commits exist in git.

The single gap is test coverage for table integrity (INGEST-07): the `test_chunking_table_integrity` stub was declared as "implemented in Plan 02-04" but remains skipped. The implementation mechanism (LLM prompt) is in place — only the automated behavioral test is absent. This requires human verification with a real document and live API key.

Notable deviations from plan specs (all improvements, none regressions):
- `ingestion_service.ingest_document` accepts injected `openai_client` and `qdrant_client` parameters instead of constructing them internally — enables better testability, correctly wired via FastAPI `Depends()`.
- Re-ingestion uses write-then-replace (`upsert → delete_by_source_except_new`) instead of pre-delete (`delete → upsert`) for zero-downtime atomicity.
- Chunking uses `re.split(r'\n?^---$\n?', ..., flags=re.MULTILINE)` instead of `raw.split("\n---\n")` to handle varied LLM output formatting.
- 50MB upload size limit enforced in router (improvement over plan spec).

---

_Verified: 2026-05-06T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
