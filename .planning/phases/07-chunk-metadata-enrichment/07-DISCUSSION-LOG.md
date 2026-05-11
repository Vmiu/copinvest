# Phase 7: Chunk Metadata Enrichment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-11
**Phase:** 07-chunk-metadata-enrichment
**Mode:** discuss
**Areas discussed:** Metadata extraction strategy, Document registry schema changes, Qdrant payload indexes

## Areas Discussed

### Metadata Extraction Strategy

| Question | Options Presented | Selection |
|----------|------------------|-----------|
| How should the 11 fields be sourced? | Caller-supplied + computed / LLM inference / Docling structured output + caller-supplied | Caller-supplied + computed |
| How to extract page_number, section_heading, is_table, is_figure? | Parse from existing markdown / Second LLM pass / Best-effort only | Parse from existing markdown output |

### Document Registry Schema Changes

| Question | Options Presented | Selection |
|----------|------------------|-----------|
| Add new fields to document_registry DB? | Add all columns / Qdrant-only / Minimal (type + jurisdiction only) | Add columns to document_registry |
| How does parent_doc_title relate to filename? | Separate display title / Replaces filename / Defaults to filename | Separate display title alongside filename |

### Qdrant Payload Indexes

| Question | Options Presented | Selection |
|----------|------------------|-----------|
| Which new fields get Qdrant indexes? | document_type / jurisdiction / language / is_table + is_figure | document_type, is_table, is_figure |

## Claude's Discretion Items

- Re-ingestion trigger mechanism
- Exact regex for section_heading extraction
- Page number assignment for cross-page chunks
- product_codes input format in upload form

## Deferred Ideas

None.
