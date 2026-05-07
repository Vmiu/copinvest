---
phase: 3
slug: rag-query-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_query.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_query.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | RAG-01 | — | N/A | migration | `uv run alembic upgrade head` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | RAG-01 | — | N/A | unit | `uv run pytest tests/test_query.py::test_session_24h_timeout -q` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | RAG-01 | — | N/A | unit | `uv run pytest tests/test_query.py::test_audit_new_fields -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | RAG-01 | — | N/A | unit | `uv run pytest tests/test_query.py::test_query_rewrite -q` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | RAG-04 | — | N/A | unit | `uv run pytest tests/test_query.py::test_rerank_threshold -q` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 2 | RAG-02 | — | N/A | unit | `uv run pytest tests/test_query.py::test_citation_extraction -q` | ❌ W0 | ⬜ pending |
| 3-02-04 | 02 | 2 | RAG-03 | — | N/A | unit | `uv run pytest tests/test_query.py::test_not_found_sentinel -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | RAG-01 | — | JWT required | integration | `uv run pytest tests/test_query.py::test_query_endpoint_happy_path -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 3 | RAG-03 | — | N/A | integration | `uv run pytest tests/test_query.py::test_query_not_found -q` | ❌ W0 | ⬜ pending |
| 3-03-03 | 03 | 3 | AUTH-04 | T-3-01 | RBAC pre-filter blocks lower-tier access | integration | `uv run pytest tests/test_query.py::test_query_rbac_enforcement -q` | ❌ W0 | ⬜ pending |
| 3-03-04 | 03 | 3 | AUDIT-01 | — | Audit record created for every query | integration | `uv run pytest tests/test_query.py::test_query_audit_record -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_query.py` — stubs for RAG-01 through RAG-05 and RBAC/audit tests
- [ ] `tests/conftest.py` — add query-specific fixtures (mock Qdrant results, mock reranker response)

*Existing pytest infrastructure covers framework setup — only new test file and fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Answer quality with real documents | RAG-01, RAG-02 | Requires real Qdrant + real API keys | POST /api/v1/query with a question about an ingested document; verify answer cites correct source |
| Not-found with real LLM | RAG-03, RAG-05 | Requires live DeepSeek API | POST /api/v1/query with "What is the weather today?"; verify not_found: true |
| Reranker score distribution | RAG-04 | Requires real OpenRouter API | Check audit log chunks_passed_rerank field after a real query |
