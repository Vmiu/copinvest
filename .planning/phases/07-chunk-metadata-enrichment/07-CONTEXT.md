# Phase 7: Chunk Metadata Enrichment - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Every chunk in Qdrant carries the 11 enriched metadata fields; the document registry reflects the new schema. Re-ingestion is idempotent. Admin can filter the document registry by document_type and jurisdiction.

</domain>

<decisions>
## Implementation Decisions

### Metadata Extraction Strategy
- **D-01:** Doc-level fields (document_type, language, jurisdiction, product_codes, parent_doc_title) are caller-supplied at ingest time via the upload form/API.
- **D-02:** Computed fields are extracted from existing markdown output — no additional LLM calls:
  - `page_number` — from `<!-- Page N -->` markers already in vision LLM output
  - `section_heading` — last `#`/`##`/`###` heading seen before the chunk in the markdown
  - `is_table` — chunk contains a markdown table (`|` character pattern)
  - `is_figure` — chunk contains a figure description from the vision prompt output
- **D-03:** `chunk_position` (first/middle/last) and `total_chunks_in_doc` are computed after chunking completes, before upsert.

### Document Registry Schema
- **D-04:** Add columns to `document_registry` DB table: `document_type`, `language`, `jurisdiction`, `product_codes` (JSON text), `parent_doc_title`. Enables SQL filtering in admin UI without coupling to Qdrant.
- **D-05:** `parent_doc_title` is a separate human-readable display name set by admin at upload time (e.g. "HSBC Annual Report 2024"). `filename` stays as the original file name. Both coexist on the record.

### Qdrant Payload Indexes
- **D-06:** Add payload indexes for: `document_type` (KEYWORD), `is_table` (BOOL), `is_figure` (BOOL). These are the fields needed for Phase 8 agent skills (table/figure scoped retrieval) and admin UI filtering.
- **D-07:** `jurisdiction` and `language` are NOT indexed in Qdrant — filtering for these happens at the DB layer via document_registry.

### Re-ingestion
- **D-08:** Claude's discretion — admin-triggered bulk re-ingest via API or migration script. Existing write-then-replace atomicity pattern handles safety.

### Claude's Discretion
- Re-ingestion trigger mechanism (admin API endpoint vs standalone script)
- Exact regex patterns for section_heading extraction
- Handling of chunks that span page boundaries (page_number assignment)
- product_codes input format (comma-separated string vs JSON array in the upload form)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Metadata requirements
- `.planning/REQUIREMENTS.md` §META-01 — Full list of 11 required fields with types

### Existing ingestion pipeline
- `backend/services/ingestion_service.py` — Current ingest flow; payload_base construction at line 84
- `backend/services/chunking_service.py` — chunk_document() returns list[str]; page markers in _split_pages()
- `backend/services/document_parser.py` — Vision LLM output format with `<!-- Page N -->` markers
- `backend/repositories/vector_repo.py` — upsert_chunks() payload structure; setup_collection() for indexes
- `backend/models/document.py` — DocumentRecord ORM model to extend
- `backend/schemas/document.py` — DocumentListItem schema to extend

### Alembic migrations
- `alembic/` — Migration pattern for DB schema changes (used in Phase 1)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_split_pages()` in chunking_service.py: already splits on `<!-- Page N -->` markers — page_number can be tracked here
- `delete_by_source_except_new()` in vector_repo.py: write-then-replace atomicity already handles re-ingestion safely
- `setup_collection()` in vector_repo.py: idempotent index creation pattern — extend for new indexes
- `upsert_chunks()` in vector_repo.py: `payload_base` dict is spread into each point — new fields slot in here

### Established Patterns
- Payload fields are passed as `payload_base` dict from ingestion_service → vector_repo; new doc-level fields follow the same path
- DB migrations use Alembic; `DocumentRecord` ORM model is the source of truth for document_registry columns
- Ingest API accepts `sensitivity_tier` as a form field — new doc-level fields follow the same pattern

### Integration Points
- `ingest_document()` signature needs new parameters: document_type, language, jurisdiction, product_codes, parent_doc_title
- `chunk_document()` currently returns `list[str]`; needs to return richer objects or a parallel metadata list
- `DocumentListItem` schema and `DocumentListResponse` need new fields for admin UI filtering
- `setup_collection()` needs 3 new index calls (document_type, is_table, is_figure)

</code_context>

<specifics>
## Specific Ideas

- No specific UI references — open to standard approaches for the admin filter UI
- product_codes is a list[str] in the requirements; store as JSON in DB, as list in Qdrant payload

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-chunk-metadata-enrichment*
*Context gathered: 2026-05-11*
