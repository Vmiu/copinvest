---
status: partial
phase: 04-telegram-bot
source: [04-VERIFICATION.md]
started: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end query flow
expected: Send a text message to the bot, receive a sourced draft answer with an inline keyboard showing 3 buttons (Approve / Edit / Discard)
result: [pending]

### 2. Approve action
expected: Tap Approve — audit record updated with adviser_action=approved, final_response=llm_response; confirmation message sent
result: [pending]

### 3. Edit action
expected: Tap Edit — bot replies "Send your revised version:", ConversationHandler enters AWAITING_EDIT state; send replacement text — audit record updated with adviser_action=edited, final_response=replacement text; "Revised response recorded." sent
result: [pending]

### 4. Discard action
expected: Tap Discard — audit record updated with adviser_action=discarded, final_response=None; "Response discarded." sent
result: [pending]

### 5. Unregistered user rejection
expected: Message from a Telegram user ID not in TELEGRAM_USER_MAP receives "Your Telegram account is not registered. Contact your administrator." — no RAG query is processed
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
