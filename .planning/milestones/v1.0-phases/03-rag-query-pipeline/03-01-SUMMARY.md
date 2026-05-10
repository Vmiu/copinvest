---
phase: 03-rag-query-pipeline
plan: "03-01"
subsystem: backend
tags: [schema, migration, models, services, test-scaffold]
dependency_graph:
  requires: [02-04]
  provides: [query-pipeline-schema, session-24h-timeout, update-query-fields]
  affects: [03-02, 03-03]
tech_stack:
  added: []
  patterns: [alembic-add-column, mapped-column-nullable, progressive-audit-lifecycle]
key_files:
  created:
    - alembic/versions/a1b2c3d4e5f6_add_query_pipeline_fields.py
    - tests/test_query.py
  modified:
    - backend/models/audit_log.py
    - backend/services/audit_service.py
    - backend/services/session_service.py
    - backend/services/chunking_service.py
decisions:
  - "query_text serves as original_query per D-19 — no new column needed; rewritten_query is the only new audit field for query enhancement"
  - "SESSION_TIMEOUT changed from 30min to 24h per D-21; last_activity used for expiry check with fallback to start_time for backward compatibility"
  - "deepseek-chat replaced with deepseek-v4-flash per D-15 — deprecated July 2026"
metrics:
  duration: "~5min"
  completed: "2026-05-07"
  tasks_completed: 3
  files_changed: 6
---

# Phase 3 Plan 01: Schema Migration and Service Foundation Summary

Alembic migration adds four new columns for the RAG query pipeline; SQLAlchemy models, audit service, session service, and chunking service updated to match; test scaffold created with 11 skipped stubs for Plan 03-03.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Alembic migration — add query pipeline fields | 8e274d8 | alembic/versions/a1b2c3d4e5f6_add_query_pipeline_fields.py |
| 2 | Update SQLAlchemy models and services | fdb1cb4 | backend/models/audit_log.py, audit_service.py, session_service.py, chunking_service.py |
| 3 | Create test scaffold for Phase 3 | 78104ac | tests/test_query.py |

## What Was Built

**Migration (a1b2c3d4e5f6):** Adds `rewritten_query` TEXT, `chunks_passed_rerank` INTEGER, `not_found` BOOLEAN to `audit_log`; adds `last_activity` TIMESTAMP WITH TIME ZONE to `sessions`. Chained from `23b31f0ac9b4`. Upgrade and downgrade verified clean.

**Model updates:** `AuditLog` gains three new `Mapped` columns after `final_response`. `Session` gains `last_activity` after `end_time`.

**audit_service:** New `update_query_fields(db, audit, rewritten_query, chunks_passed_rerank, not_found)` function follows the existing `db.flush()` pattern.

**session_service:** `SESSION_TIMEOUT` changed from 30 minutes to 24 hours. `get_or_create_session()` now uses `last_activity or start_time` for the expiry check and sets `last_activity = now` on session reuse before returning.

**chunking_service:** Model string updated from `deepseek-chat` to `deepseek-v4-flash`.

**Test scaffold:** 11 stub functions in `tests/test_query.py`, all marked `pytest.mark.skip(reason="implemented in Plan 03-03")`. Pytest collects and skips all 11, exits 0.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Compliance

- T-3-01 (migration tampering): downgrade() reverses all four columns in reverse order — verified clean.
- T-3-02 (session expiry elevation): expiry check uses `last_activity` from DB (server-controlled), not client-supplied value; naive UTC normalization preserved from Phase 1.
- T-3-03 (audit field disclosure): accepted — internal audit fields, no new trust boundary.

## Known Stubs

`tests/test_query.py` contains 11 stub test functions. These are intentional scaffolding — Plan 03-03 will implement them. They do not prevent this plan's goal (schema + service foundation) from being achieved.

## Self-Check: PASSED

- alembic/versions/a1b2c3d4e5f6_add_query_pipeline_fields.py: FOUND
- backend/models/audit_log.py: FOUND (rewritten_query, chunks_passed_rerank, not_found, last_activity)
- backend/services/audit_service.py: FOUND (update_query_fields)
- backend/services/session_service.py: FOUND (timedelta(hours=24), last_activity update)
- backend/services/chunking_service.py: FOUND (deepseek-v4-flash)
- tests/test_query.py: FOUND (11 skipped stubs)
- Commits 8e274d8, fdb1cb4, 78104ac: FOUND in git log
