---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | AUTH-03 | — | N/A (config) | import | `python -c "from backend.core.config import Settings; ..."` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01 | 1 | AUDIT-01, AUDIT-02, AUDIT-05 | — | N/A (models) | import | `python -c "from backend.models import Base, User, AuditLog, ..."` | ❌ W0 | ⬜ pending |
| 01-01-T3 | 01 | 1 | — | — | N/A (scaffold) | install+import | `pip install -e ".[dev]" && pytest tests/ -x -q --co` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 02 | 2 | AUTH-01, AUTH-03 | T-01 | JWT signed with HS256, passwords hashed with bcrypt | unit | `SECRET_KEY=testsecret pytest tests/test_security.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-T2 | 02 | 2 | AUTH-01, AUTH-02 | T-02 | Invalid creds return 401, expired token rejected | integration | `SECRET_KEY=testsecret pytest tests/test_auth.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 03 | 2 | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05 | — | Audit records capture full trace | import | `python -c "from backend.services.audit_service import ..."` | ❌ W0 | ⬜ pending |
| 01-03-T2 | 03 | 2 | AUDIT-01..05 | T-03 | Progressive lifecycle enforced, tier recorded | unit | `SECRET_KEY=testsecret pytest tests/test_audit.py tests/test_session.py -x -q` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 04 | 3 | AUTH-04 | T-04 | Pre-retrieval RBAC filtering at Qdrant layer | import | `python -c "from backend.repositories.vector_repo import ..."` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 04 | 3 | AUTH-04, AUTH-05 | T-04 | Adviser cannot access Restricted/Confidential | unit | `SECRET_KEY=testsecret pytest tests/test_vector_repo.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (async DB session, test client, JWT helpers)
- [ ] `tests/test_auth.py` — stubs for AUTH-01..05
- [ ] `tests/test_audit.py` — stubs for AUDIT-01..05
- [ ] `pytest`, `pytest-asyncio`, `httpx` — test dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JWT persists across browser refresh | AUTH-02 | Requires browser storage behavior | 1. Login via API 2. Store token in localStorage 3. Refresh page 4. Verify token still present |
| Qdrant Docker container starts correctly | D-02 | Infrastructure dependency | 1. Run docker-compose up 2. Verify Qdrant health endpoint responds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29
