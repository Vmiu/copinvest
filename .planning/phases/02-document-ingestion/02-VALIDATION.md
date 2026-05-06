---
phase: 2
slug: document-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio 0.26 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INGEST-01 | — | N/A | integration | `uv run pytest tests/test_ingestion.py -k pdf` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INGEST-02 | — | N/A | integration | `uv run pytest tests/test_ingestion.py -k docx` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | INGEST-03 | — | N/A | integration | `uv run pytest tests/test_ingestion.py -k excel` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | INGEST-04 | — | Only compliance role can assign tier | integration | `uv run pytest tests/test_ingestion.py -k tier` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | INGEST-05 | — | Metadata matches assigned tier | unit | `uv run pytest tests/test_ingestion.py -k metadata` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | INGEST-06 | — | N/A | unit | `uv run pytest tests/test_chunking.py -k semantic` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | INGEST-07 | — | N/A | unit | `uv run pytest tests/test_chunking.py -k table` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | INGEST-08 | — | N/A | integration | `uv run pytest tests/test_ingestion.py -k metrics` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ingestion.py` — stubs for INGEST-01 through INGEST-05, INGEST-08
- [ ] `tests/test_chunking.py` — stubs for INGEST-06, INGEST-07
- [ ] `tests/conftest.py` — update with ingestion fixtures (mock OpenAI, temp files)
- [ ] `docling>=2.12.0` and `openai>=1.68.0` added to pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF table structure preserved visually | INGEST-01 | Visual inspection of markdown output | Upload a PDF with financial tables, verify markdown output preserves rows/columns |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
