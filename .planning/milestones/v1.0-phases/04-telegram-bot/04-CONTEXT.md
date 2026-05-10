# Phase 4: Telegram Bot - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Advisers query the system via Telegram, receive sourced draft answers, review each draft via inline keyboard (Approve / Edit / Discard), and every action is recorded in the audit trail. Scope: Telegram bot process, webhook/polling setup, user identity mapping, query pipeline integration, draft review flow, audit trail write-back. Web UI is Phase 5. Telegram user registration flows and RBAC-on-Telegram are v2 (TELE-V2-01, TELE-V2-02).

</domain>

<decisions>
## Implementation Decisions

### Telegram ↔ Internal User Identity
- **D-01:** Static config mapping — `TELEGRAM_USER_MAP` in `.env` / `Settings` maps `telegram_user_id` (string) → `{"user_id": "...", "role": "adviser"}`. No DB changes, no registration flow.
- **D-02:** If an incoming Telegram `user_id` is not in the map, the bot replies: "Your Telegram account is not registered. Contact your administrator." and drops the message.
- **D-03:** Role is read from the map and passed to the query pipeline as `user_role` — same RBAC pre-filter as the web endpoint.

### Draft Review Flow
- **D-04:** Bot sends the RAG answer as a draft message with an inline keyboard: `[✓ Approve] [✏ Edit] [✗ Discard]`.
- **D-05:** **Approve** — bot records `adviser_action=approved`, `final_response=llm_response`, `adviser_edited=False` in the audit log. Bot confirms: "Response approved and recorded."
- **D-06:** **Edit** — bot replies "Send your revised version:" and enters a `ConversationHandler` wait state. Adviser sends a replacement message. Bot records `adviser_action=edited`, `final_response=<replacement>`, `adviser_edited=True`. Bot confirms: "Revised response recorded."
- **D-07:** **Discard** — bot records `adviser_action=discarded`, `final_response=None`, `adviser_edited=False`. Bot confirms: "Response discarded."
- **D-08:** The inline keyboard is removed from the original draft message after any action (edit the message to remove reply_markup).
- **D-09:** `trace_id` from the query response is stored in the `ConversationHandler` context so the audit write-back can reference the correct `AuditLog` record.

### Bot Deployment
- **D-10:** Long-polling (`Application.run_polling()`) — no public HTTPS URL required. Works on localhost and single-VM deployment without SSL setup.
- **D-11:** Bot runs as a **separate process** alongside FastAPI — not mounted into the FastAPI app. Start command: `uv run python -m backend.telegram_bot`.
- **D-12:** Bot calls the query pipeline **directly as a Python function** (imports `query_service.process_query`) — not via HTTP to the FastAPI endpoint. Avoids self-HTTP and shares the same DB session factory.

### Error and Timeout Handling
- **D-13:** Bot sends `chat_action=typing` (Telegram typing indicator) immediately on receiving a query, before calling the pipeline. This gives visual feedback during processing.
- **D-14:** If the pipeline raises an exception or times out (>30s), bot sends: "Something went wrong — please try again." No retry button for v1.
- **D-15:** If Qdrant is unavailable, the error surfaces as a `RuntimeError` from `query_service` — caught and shown as the generic error message above.

### Audit Integration
- **D-16:** `channel` field in `AuditLog` is set to `"telegram"` for all bot-originated queries (existing `channel` field, new value).
- **D-17:** Audit record is created by `query_service.process_query` (same as web) — the bot passes `channel="telegram"` as a parameter.
- **D-18:** Adviser action write-back (Approve/Edit/Discard) calls `audit_repo.update_adviser_action(trace_id, action, final_response)` — a new repo method that updates `adviser_action`, `final_response`, `adviser_edited` on the existing `AuditLog` row.

### Claude's Discretion
- Exact bot command list (`/start`, `/help` etc.) beyond the query flow
- Conversation timeout for the Edit wait state (suggest 5 minutes)
- Exact wording of confirmation messages
- Whether to show source citations as a separate follow-up message or inline in the draft

</decisions>

<specifics>
## Specific Ideas

- Bot calls `query_service.process_query` directly (not via HTTP) — avoids self-HTTP and shares DB session factory.
- `ConversationHandler` is the python-telegram-bot mechanism for the Edit wait state — required for multi-step flows.
- Long-polling chosen over webhook — no SSL/public URL needed for single-VM deployment.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Telegram Bot (Primary Adviser Interface)" — TELE-01 through TELE-04 (the four acceptance criteria for this phase)

### Prior phase decisions (integration points)
- `.planning/phases/03-rag-query-pipeline/03-CONTEXT.md` — Query pipeline decisions: endpoint shape, audit lifecycle, session management, `process_query` signature
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — Auth, RBAC, `AuditLog` model design, `AdviserAction` enum

### Codebase
- `backend/services/query_service.py` — `process_query()` function the bot calls directly
- `backend/repositories/audit_repo.py` — Audit write-back; new `update_adviser_action` method needed here
- `backend/models/audit_log.py` — `AuditLog` model with `adviser_action`, `final_response`, `adviser_edited`, `channel` fields
- `backend/models/enums.py` — `AdviserAction` enum (`approved/edited/discarded`) already defined
- `backend/core/config.py` — `Settings` class; `TELEGRAM_USER_MAP` and `TELEGRAM_BOT_TOKEN` need adding

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/query_service.py` — `process_query(db, query, session_id, user_id, user_role, ...)` — bot calls this directly, passing `channel="telegram"`
- `backend/repositories/audit_repo.py` — existing audit write patterns; needs one new method for adviser action write-back
- `backend/models/enums.py` — `AdviserAction.approved/edited/discarded` already defined; no enum changes needed
- `backend/core/config.py` — `get_settings()` with `lru_cache`; add `telegram_bot_token: str` and `telegram_user_map: str` (JSON string, parsed at runtime)

### Established Patterns
- Services receive DB session and clients as parameters (not via `get_settings()` inside service) — bot must follow same pattern
- `audit_repo` uses `db.flush()` not `db.commit()` — caller controls transaction boundary
- `channel` field in `AuditLog` is a plain `String` — `"telegram"` is a valid new value, no migration needed
- `require_role()` dependency is FastAPI-specific — bot bypasses it and does its own identity check via the static map

### Integration Points
- Bot process imports `backend.services.query_service` and `backend.core.database` directly
- Bot needs its own `AsyncSession` factory — same `async_sessionmaker` from `backend.core.database`
- `trace_id` from `process_query` result must be threaded through `ConversationHandler` context to the audit write-back callback

</code_context>

<deferred>
## Deferred Ideas

- Telegram user registration flow (/start → pending → admin approval) — TELE-V2-01 in REQUIREMENTS.md
- RBAC on Telegram (role-based access control applied to Telegram queries) — TELE-V2-02
- Retry button on error — keep simple for v1

</deferred>

---

*Phase: 04-telegram-bot*
*Context gathered: 2026-05-08*
