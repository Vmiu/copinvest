# Phase 2: Document Ingestion - Context

**Gathered:** 2026-05-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Parse PDF, Word (.docx), and Excel/CSV documents, chunk them with LLM-based semantic awareness, tag metadata (sensitivity tier, roles, source), and embed into Qdrant. Admins (compliance role) trigger ingestion via REST API and assign sensitivity tiers. Query pipeline and UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Chunking strategy
- **D-01:** LLM-based semantic chunking — documents are first parsed by docling, then sent to gpt-4o-mini which reformats content into natural semantic chunks
- **D-02:** LLM decides chunk boundaries naturally based on content structure — no strict token target
- **D-03:** Tables are never split across chunks regardless of size (INGEST-07)
- **D-04:** Single universal chunking prompt for all document types (PDF, Word, Excel) — no per-format specialization
- **D-05:** Each chunk carries: source_id, doc_type, sensitivity_tier, allowed_roles, chunk_index, section_title (INGEST-05)
- **D-06:** Embedding model: text-embedding-3-small (1536 dims) — matches existing Qdrant collection from Phase 1

### LLM chunking prompt design
- **D-07:** LLM returns markdown with `---` separators between chunks — requires post-processing to split
- **D-08:** On LLM failure: retry up to 2 times, then fail the entire document. No fallback to structural splitting — only LLM-quality chunks enter the system

### Ingestion API design
- **D-09:** REST endpoint only (POST /api/ingest) — no CLI script. Future admin UI (Phase 5) calls this endpoint
- **D-10:** Single file per request with sensitivity_tier as form field. Batch = multiple sequential calls
- **D-11:** Only compliance role can trigger ingestion (authorization enforced at endpoint)
- **D-12:** Re-ingestion replaces: delete all existing chunks for that document_id, then re-ingest from scratch

### Document identity
- **D-13:** Admin provides an explicit document_id (human-readable slug) at upload time for replacement matching
- **D-14:** document_id is optional — if omitted, system generates a UUID. When provided, re-upload with same ID triggers replacement

### Processing model
- **D-15:** Synchronous processing — request waits until full pipeline completes (parse → LLM chunk → embed → store). Returns 201 with results

### Parsing quality & logging
- **D-16:** Quality metrics stored in document registry DB table: char_count, chunk_count, warnings (JSON), parse_duration_ms, extraction_method (INGEST-08)
- **D-17:** On parse failure (docling can't process the document): fail entire document with HTTP 422 and error details. No partial ingestion

### Claude's Discretion
- Exact LLM chunking system prompt wording
- Document registry table schema details beyond the specified fields
- Error message formatting
- Request validation details (file size limits, allowed MIME types)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 foundation (integration points)
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — RBAC tier mapping, Qdrant collection config, sensitivity tier enum
- `backend/models/enums.py` — SensitivityTier and UserRole enums (source of truth for tier/role values)
- `backend/repositories/vector_repo.py` — QdrantVectorRepository with RBAC pre-filtering (integration point for storing chunks)
- `backend/core/config.py` — Settings class with Qdrant connection config

### Requirements
- `.planning/REQUIREMENTS.md` §INGEST-01 through INGEST-08 — All ingestion requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `QdrantVectorRepository` (backend/repositories/vector_repo.py): Already has `upsert_documents()` and `delete_by_source()` methods — direct integration point for storing chunks and handling re-ingestion
- `SensitivityTier` enum (backend/models/enums.py): Integer enum (1-4) already used in Qdrant payload filtering
- `UserRole` enum (backend/models/enums.py): Defines adviser/senior_adviser/compliance/admin roles
- `Settings` class (backend/core/config.py): Has qdrant_url, qdrant_api_key, openai_api_key, collection_name

### Established Patterns
- Async SQLAlchemy sessions via `get_db()` dependency
- Pydantic v2 models for request/response validation
- JWT auth with role-based access via `get_current_user` dependency
- Repository pattern (vector_repo separates Qdrant operations from business logic)

### Integration Points
- New ingestion endpoint connects to existing FastAPI app
- Chunks stored via existing `QdrantVectorRepository.upsert_documents()`
- Auth/role check via existing JWT middleware
- Document registry table needs Alembic migration (extends existing DB)

</code_context>

<specifics>
## Specific Ideas

- LLM-first chunking philosophy: the user wants the LLM to be the intelligence layer that decides semantic boundaries, not a rule-based splitter
- "Let LLM decide the semantic chunks" — trust the model to understand document structure
- Tables must never be split — this is a hard requirement from INGEST-07, not a preference

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-document-ingestion*
*Context gathered: 2026-05-01*
