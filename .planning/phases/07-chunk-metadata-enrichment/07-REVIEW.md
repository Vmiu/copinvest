---
status: issues_found
files_reviewed: 11
critical: 0
warning: 1
info: 3
total: 4
depth: standard
reviewed_at: 2026-05-13
---

# Code Review: Phase 7 — Chunk Metadata Enrichment

**Depth:** standard | **Files:** 11 | **Date:** 2026-05-13

---

## Findings

### WR-01: upsert_document_record skips new metadata fields on re-ingestion

**File:** `backend/repositories/document_repo.py:14-28`
**Severity:** Warning
**Category:** Bug — Data Integrity

`upsert_document_record()` copies only the original Phase 1 fields (`filename`, `doc_type`, `sensitivity_tier`, `chunk_count`, etc.) to the existing record on update. The 5 new Phase 7 fields — `document_type`, `language`, `jurisdiction`, `product_codes`, `parent_doc_title` — are **not copied** to `existing` before `db.flush()`.

**Impact:** When the same `document_id` is re-ingested with different metadata (e.g., corrected `jurisdiction` or `document_type`), the old values persist in the `document_registry` table. The Qdrant payload gets the new values (correct via `upsert_chunks`), but the DB registry is stale.

**Expected:** All 5 new fields should be copied in the update branch, mirroring the field-by-field pattern already used for `filename`, `doc_type`, etc.

**Reproduction:**
```python
# Ingest document_id="X" with jurisdiction="HK"
# Re-ingest document_id="X" with jurisdiction="SG"
# DocumentRecord.query shows jurisdiction="HK" (stale)
```

---

### IN-01: json.loads() on product_codes can raise unhandled 500

**File:** `backend/routers/documents.py:28`
**Severity:** Info
**Category:** Robustness

```python
data["product_codes"] = json.loads(d.product_codes) if d.product_codes else []
```

If the `product_codes` column contains malformed JSON (e.g., from a manual DB edit or migration bug), `json.loads()` raises `json.JSONDecodeError`, which propagates as an unhandled 500. Consider wrapping in try/except and returning an empty list or logging the corruption.

---

### IN-02: Dead imports in vector_repo.py

**File:** `backend/repositories/vector_repo.py:147`
**Severity:** Info
**Category:** Code Quality

```python
from qdrant_client.models import HasIdCondition, IsEmptyCondition  # noqa: F401
```

Both `HasIdCondition` and `IsEmptyCondition` are imported but never referenced in the function body. The `# noqa: F401` comment suppresses the linter but doesn't remove the dead code. These can be removed.

---

### IN-03: is_table detection uses simple heuristic

**File:** `backend/services/chunking_service.py:97`
**Severity:** Info
**Category:** Code Quality — False Positive Risk

```python
"is_table": "|" in chunk and chunk.count("|") >= 2,
```

Chunks containing pipe characters in non-table contexts (e.g., `|` in regex examples, shell commands, or value separators) would be incorrectly flagged as `is_table: True`. Consider using a stricter regex pattern matching markdown table syntax (e.g., `|` followed by `\n|-`).

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Warning  | 1 |
| Info     | 3 |
| **Total** | **4** |

**Key issue:** WR-01 is the only actionable bug — re-ingestion doesn't update the 5 new metadata columns in the DB registry. Qdrant payload is correct; only the SQLite `document_registry` table is stale on re-ingestion.

**Overall assessment:** Phase 7 is solid. The core chunking metadata extraction pipeline works correctly, tests validate all 11 META-01 fields, and idempotency is verified. The WR-01 fix is a one-line-per-field addition to `upsert_document_record`.
