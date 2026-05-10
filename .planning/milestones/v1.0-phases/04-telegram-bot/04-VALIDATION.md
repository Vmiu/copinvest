---
phase: 4
slug: telegram-bot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_telegram.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_telegram.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | TELE-01, TELE-04 | T-04-01, T-04-02 | channel param defaults to "web"; update_adviser_action raises ValueError on unknown trace_id | unit | `uv run pytest tests/test_audit.py -q` | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | TELE-02 | T-04-01 | telegram_bot_token has empty default (never logged) | unit | `uv run python -c "from backend.core.config import Settings; s = Settings(secret_key='x', deepseek_api_key='x', openroute_api_key='x', voyage_api_key='x'); print(s.telegram_bot_token)"` | ✅ | ⬜ pending |
| 4-02-01 | 02 | 2 | TELE-02 | T-04-04 | unregistered user gets error message, no query processed | unit | `uv run python -c "from backend.telegram_bot.identity import get_user_from_telegram_id; print('ok')"` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | TELE-01, TELE-02, TELE-03, TELE-04 | T-04-04, T-04-05, T-04-06, T-04-08 | handle_query sends draft with keyboard; handle_action validates callback_data via AdviserAction enum | unit | `uv run python -c "from backend.telegram_bot.handlers import handle_query, handle_action, handle_edit_reply, AWAITING_EDIT; print('ok')"` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 3 | TELE-01, TELE-04 | T-04-02, T-04-09 | update_adviser_action raises ValueError on unknown trace_id | unit | `uv run pytest tests/test_telegram.py -k "adviser_action" -v` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 3 | TELE-01, TELE-02, TELE-03, TELE-04 | T-04-04, T-04-05, T-04-06, T-04-10 | generic error message on pipeline failure; no internal details leaked | unit | `uv run pytest tests/test_telegram.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_telegram.py` — stubs for TELE-01 through TELE-04 (created in plan 04-03)
- [ ] `backend/telegram_bot/__init__.py` — package marker (created in plan 04-02)

*Note: pytest-asyncio and conftest.py fixtures already exist from prior phases. No new framework installation needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bot receives real Telegram message and returns sourced answer | TELE-01 | Requires live Telegram bot token and registered user | Set TELEGRAM_BOT_TOKEN and TELEGRAM_USER_MAP in .env; run `uv run python -m backend.telegram_bot`; send a text message from a registered Telegram account |
| Inline keyboard appears and buttons are tappable | TELE-03 | Requires live Telegram client | After sending a query, verify Approve/Edit/Discard buttons appear in the Telegram app |
| Edit flow: replacement text is recorded | TELE-03, TELE-04 | Requires live Telegram interaction | Tap Edit, send replacement text, verify "Revised response recorded." confirmation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (❌ W0 tasks covered by plan 04-03)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
