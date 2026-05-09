---
status: passed
phase: 04-telegram-bot
source: [04-VERIFICATION.md]
started: 2026-05-09T00:00:00Z
updated: 2026-05-09T04:39:04Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end query flow
expected: Send a text message to the bot, receive a sourced draft answer with an inline keyboard showing 3 buttons (Approve / Edit / Discard)
result: passed

### 2. Approve action
expected: Tap Approve — audit record updated with adviser_action=approved, final_response=llm_response; confirmation message sent
result: passed

### 3. Edit action
expected: Tap Edit — bot replies "Send your revised version:", ConversationHandler enters AWAITING_EDIT state; send replacement text — audit record updated with adviser_action=edited, final_response=replacement text; "Revised response recorded." sent
result: passed

### 4. Discard action
expected: Tap Discard — audit record updated with adviser_action=discarded, final_response=None; "Response discarded." sent
result: passed

### 5. Unregistered user rejection
expected: Message from a Telegram user ID not in TELEGRAM_USER_MAP receives "Your Telegram account is not registered. Contact your administrator." — no RAG query is processed
result: passed

## Summary

total: 5
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
