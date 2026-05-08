# Phase 4: Telegram Bot - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 04-telegram-bot
**Areas discussed:** Telegram ↔ internal user identity, Draft review flow mechanics, Error and timeout handling

---

## Telegram ↔ Internal User Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Static config mapping in .env / settings | Hardcoded dict maps telegram_user_id → internal user_id + role. No DB changes, works for single-firm prototype. | ✓ |
| /start registration flow | Adviser sends /start, bot creates pending mapping, admin approves. Adds registration flow to this phase. | |
| Admin-managed DB mapping | Admin runs CLI or hits API to register telegram_user_id → user_id pairs in DB. | |

**User's choice:** Static config mapping in .env / settings
**Notes:** Appropriate for v1 prototype. TELE-V2-01 (proper user mapping) deferred to v2.

---

## Draft Review Flow Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Bot prompts for a replacement message | Adviser taps Edit, bot replies "Send your revised version:", adviser types replacement, bot records it. | ✓ |
| Inline text editing | Edit opens original draft in Telegram inline edit field (not natively supported — workaround required). | |
| Edit = Discard + note to revise manually | Edit treated same as Discard; adviser handles editing outside the bot. | |

**User's choice:** Bot prompts for a replacement message
**Notes:** Requires ConversationHandler from python-telegram-bot for the multi-step wait state.

---

## Error and Timeout Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Friendly error message + typing indicator | Bot sends typing indicator while processing; on error sends "Something went wrong — please try again." | ✓ |
| Error message + Retry button | Error message with inline Retry button that re-runs the same query. | |
| Silent failure | Bot sends nothing on error — adviser must re-send. | |

**User's choice:** Friendly error message + typing indicator
**Notes:** Retry button deferred to v2 — keep simple for v1.

---

## Claude's Discretion

- Exact bot command list (/start, /help etc.) beyond the query flow
- Conversation timeout for the Edit wait state
- Exact wording of confirmation messages
- Whether source citations appear inline in the draft or as a follow-up message

## Deferred Ideas

- Telegram user registration flow (/start → pending → admin approval) — TELE-V2-01
- RBAC on Telegram queries — TELE-V2-02
- Retry button on pipeline error — v2
