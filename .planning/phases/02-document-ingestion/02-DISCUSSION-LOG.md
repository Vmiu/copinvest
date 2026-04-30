# Phase 2: Document Ingestion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-01
**Phase:** 02-document-ingestion
**Areas discussed:** Chunking strategy, Ingestion API design, Parsing quality & logging, LLM chunking prompt design, Document identity & dedup, Ingestion processing model

---

## Chunking strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Structure-based | Split on section headers and paragraph breaks from docling's markdown output | |
| Sentence-window with overlap | Use LlamaIndex's SentenceSplitter with overlap | |
| LLM-based semantic chunking | User suggested via "Other" — send parsed content to LLM for intelligent chunking | ✓ |

**User's choice:** LLM-based semantic chunking (user-initiated via free text)
**Notes:** User wants the LLM to be the intelligence layer for chunking decisions

### Chunking model

| Option | Description | Selected |
|--------|-------------|----------|
| gpt-4o chunking | Higher quality, ~$0.01-0.05 per page | |
| gpt-4o-mini chunking | Cheaper (~10x less), fast enough for structural reformatting | ✓ |

**User's choice:** gpt-4o-mini

### Chunk size target

| Option | Description | Selected |
|--------|-------------|----------|
| 500-1000 tokens | Good balance for retrieval precision | |
| 200-500 tokens | More granular retrieval | |
| LLM decides naturally | Chunks vary based on content structure | ✓ |

**User's choice:** LLM decides naturally

### Table handling

| Option | Description | Selected |
|--------|-------------|----------|
| Never split tables | Tables always kept as single chunks regardless of size | ✓ |
| Split large tables by row groups | Large tables split with repeated headers | |

**User's choice:** Never split tables

### Chunk metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Standard metadata | source_id, doc_type, sensitivity_tier, allowed_roles, chunk_index, section_title | ✓ |
| Standard + page/heading context | Adds page_number and parent_heading | |

**User's choice:** Standard metadata

### Embedding model

| Option | Description | Selected |
|--------|-------------|----------|
| text-embedding-3-small | 1536 dims, matches existing Qdrant collection | ✓ |
| text-embedding-3-large | 3072 dims, higher quality but requires collection recreation | |

**User's choice:** text-embedding-3-small (consistent with Phase 1)

### Chunking prompt scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single universal prompt | One prompt handles all doc types | ✓ |
| Per-format prompts | Different prompts for PDF, Word, Excel | |

**User's choice:** Single universal prompt

---

## LLM chunking prompt design

### Output format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON array of chunks | Structured, easy to parse programmatically | |
| Markdown with separators | Simpler prompt, requires post-processing | ✓ |

**User's choice:** Markdown with --- separators

### LLM failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Retry then fallback | Retry 2x, then fall back to structural splitting | |
| Retry then fail document | Retry 2x, then fail entire ingestion | ✓ |
| Fail immediately | No retry, immediate failure | |

**User's choice:** Retry then fail document — only LLM-quality chunks enter the system

---

## Ingestion API design

### API surface

| Option | Description | Selected |
|--------|-------------|----------|
| REST endpoint only | POST /api/ingest, callable from curl/tests/future UI | ✓ |
| REST endpoint + CLI script | Both REST and CLI for bulk loading | |
| CLI script only | Simpler, no auth needed for dev | |

**User's choice:** REST endpoint only

### Upload flow

| Option | Description | Selected |
|--------|-------------|----------|
| Single file per request | Simple, easy to test | ✓ |
| Multi-file shared tier | Multiple files, same sensitivity tier | |
| Multi-file per-file tiers | Most flexible but complex | |

**User's choice:** Single file per request

### Auth scope

| Option | Description | Selected |
|--------|-------------|----------|
| Compliance only | Only compliance role can ingest | ✓ |
| Senior adviser + compliance | Broader access | |
| Any authenticated user | Least restrictive | |

**User's choice:** Compliance only

### Re-ingestion behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Replace (delete + re-ingest) | Clean slate, no stale chunks | ✓ |
| Append (keep old + add new) | Allows versioning but risks duplicates | |
| Block (require manual delete) | Safest but more friction | |

**User's choice:** Replace

---

## Document identity & dedup

### Identity mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Filename match | Match by original filename | |
| Content hash (SHA-256) | Identical content = same document | |
| Explicit document ID | Admin provides document_id at upload | ✓ |

**User's choice:** Explicit document ID — gives admin full control over versioning

### Document ID requirement

| Option | Description | Selected |
|--------|-------------|----------|
| Optional slug, UUID fallback | Human-readable slug optional, UUID if omitted | ✓ |
| Always required | Must provide ID for every upload | |

**User's choice:** Optional slug with UUID fallback

---

## Ingestion processing model

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous | Wait for full pipeline completion | ✓ |
| Async with status polling | Return 202, process in background | |

**User's choice:** Synchronous

---

## Parsing quality & logging

### Metrics storage

| Option | Description | Selected |
|--------|-------------|----------|
| DB record per document | Store in document registry table, queryable from admin UI | ✓ |
| Structured logs only | Write to structlog, not queryable from UI | |
| Both DB + logs | DB for admin visibility + logs for ops monitoring | |

**User's choice:** DB record per document

### Parse failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fail entire document | HTTP 422, no partial ingestion | ✓ |
| Partial ingestion with warnings | Ingest what succeeded, skip failures | |
| Queue for retry | 202 Accepted, process async | |

**User's choice:** Fail entire document

---

## Claude's Discretion

- Exact LLM chunking system prompt wording
- Document registry table schema details beyond specified fields
- Error message formatting
- Request validation details (file size limits, allowed MIME types)

## Deferred Ideas

None — discussion stayed within phase scope
