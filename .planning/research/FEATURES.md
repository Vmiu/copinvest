# Feature Landscape

**Domain:** Compliance-aware RAG assistant for HK investment advisers
**Researched:** 2026-04-29
**Confidence:** MEDIUM-HIGH (strong ecosystem signal; HK SFC specifics from secondary sources)

---

## Table Stakes

Features users expect. Missing = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Document Q&A (natural language) | Core RAG value prop — advisers ask questions, get answers from internal docs | Medium | Must handle PDF, Word, Excel/CSV; layout-aware chunking critical for financial tables |
| Source attribution on every response | Regulatory requirement (SFC 24EC55); users won't trust answers without it | Medium | Inline citations with doc name, page/section; not just a footnote list |
| Full audit trail | SFC requires firms to demonstrate advice derived from approved materials; non-negotiable for licensed corps | High | Log: query text, retrieved chunks + scores, generated output, user identity, timestamp, any edits |
| Role-based document access | Advisers must not see documents above their clearance tier; fiduciary and compliance requirement | Medium | Metadata-filtered retrieval at query time, not just UI gating |
| Meeting brief generation | Replaces 30–60 min manual prep; primary workflow pain point | Medium | Synthesize client context + relevant internal docs into structured brief |
| Compliant follow-up note drafting | Post-meeting documentation is a regulatory obligation; advisers need first drafts fast | Medium | Template-aware, cites source docs, flags anything requiring adviser review |
| Product information summarization | Advisers need quick factsheet summaries without reading 40-page PDFs | Low-Medium | Summarize from ingested factsheets; cite source document |
| Human-in-the-loop review | SFC circular 24EC55 explicitly requires human oversight before AI output reaches clients | Low | UI must make it clear output is a draft; no auto-send or auto-file |
| Confidence / uncertainty signaling | Presenting all AI output with equal confidence is a compliance and trust failure | Medium | Surface low-confidence answers differently; "I couldn't find this in approved docs" is a valid response |

---

## Differentiators

Features that set the product apart. Not universally expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Sensitivity-tiered retrieval (not just RBAC) | Most tools do UI-level access control; metadata-filtered vector retrieval at query time is stronger and auditable | Medium | Tier documents at ingest (Public / Internal / Confidential / Restricted); filter at retrieval, not just display |
| Telegram bot as secondary channel | Advisers want quick mobile access without opening a full web app; no competitor in the HK adviser space does this well | Medium | Scoped to read-only Q&A and brief retrieval; no draft generation via Telegram (compliance risk) |
| Adviser edit tracking in audit log | Most tools log the AI output; logging what the adviser changed before sending is the differentiator for SFC defensibility | Medium | Diff between AI draft and final sent version; stored immutably |
| Document ingestion with table extraction | Financial docs (factsheets, portfolio exports) are table-heavy; naive chunkers destroy structure | High | Layout-aware parsing (e.g., unstructured.io or LlamaParse) for PDFs with tables; structured parsing for Excel/CSV |
| Compliance guardrail layer | Explicit check before output: does this response contain specific investment advice, price targets, or forward-looking statements without appropriate caveats? | High | Prompt-level guardrails + output classification; flag or block non-compliant drafts |
| "No answer" discipline | Returning "I couldn't find this in approved documents" rather than hallucinating is a trust differentiator in regulated contexts | Low | Requires retrieval confidence thresholds and explicit fallback messaging |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Autonomous advice delivery | SFC requires human review; auto-sending AI-generated advice to clients is a regulatory violation | Always produce drafts for adviser review; never auto-send |
| Real-time market data / price lookups | Model training data goes stale; live prices require licensed data feeds and add regulatory complexity | Scope to internal static documents only; explicitly disclaim no live data |
| Specific investment recommendations ("buy X") | Personalized investment advice requires SFC licensing; the tool assists advisers, it doesn't replace them | Frame all output as "information from approved documents" not "advice" |
| CRM write-back in v1 | Adds integration complexity, data integrity risk, and scope creep; read-only is safer to validate first | Read from CRM exports; write-back is a v2 feature after workflow is validated |
| Multi-LLM provider switching | Adds abstraction complexity with no v1 benefit; OpenAI is sufficient | Commit to OpenAI; abstract the client interface cleanly so switching is possible later without building it now |
| Meeting transcription / recording | Separate compliance domain (recording consent, data retention); out of scope for a document RAG tool | Advisers paste or type meeting notes; transcription is a separate product |
| Confidence scores as raw numbers | Showing "87% confidence" to non-technical users creates false precision and misplaced trust | Use qualitative signals: "Found in approved documents" vs "Not found — adviser should verify" |
| Open-ended internet search | Mixing internal approved docs with external web content destroys the compliance boundary | Retrieval must be strictly scoped to ingested internal documents |

---

## Feature Dependencies

```
Document ingestion pipeline
  → Document Q&A (requires indexed docs)
  → Meeting brief generation (requires indexed client context docs)
  → Product summarization (requires indexed factsheets)
  → Follow-up note drafting (requires indexed templates + compliance docs)

Role-based document access (sensitivity tiers)
  → Must be implemented before any retrieval feature ships
  → Audit trail must capture which tier was accessed per query

Source attribution
  → Required by every generation feature (Q&A, briefs, notes, summaries)
  → Depends on chunk-level metadata preserved through ingestion pipeline

Audit trail
  → Depends on user identity (auth system must exist first)
  → Must capture: query → retrieved chunks → generated output → adviser edits

Compliance guardrail layer
  → Depends on generation pipeline being stable
  → Applied as post-generation filter before output is shown to adviser

Telegram bot
  → Depends on core Q&A API being stable and auth working
  → Scoped to read-only Q&A; does not expose draft generation endpoints
```

---

## MVP Recommendation

Prioritize in this order:

1. Document ingestion pipeline (PDF, Word, Excel/CSV with metadata + sensitivity tier tagging)
2. Role-based retrieval with sensitivity filtering
3. Document Q&A with source attribution
4. Audit trail (query + retrieval + output logging)
5. Meeting brief generation
6. Follow-up note drafting
7. Product summarization

Defer:
- Telegram bot: Validate core web workflow first; Telegram adds channel complexity without proving the core value
- Compliance guardrail layer: Start with prompt-level guardrails; a dedicated classification layer is a v2 hardening step
- Adviser edit tracking in audit log: Implement basic audit trail first; diff tracking is an enhancement once the log structure is stable

---

## HK SFC Regulatory Context

The SFC circular 24EC55 (Nov 2024) sets the compliance floor for licensed corporations using generative AI:

- Senior management accountability for AI use
- Human oversight required before AI output affects clients
- Documentation of how models are selected, tested, and monitored
- Audit trails for AI-assisted decisions
- Risk management for hallucination, bias, and data leakage

This means the audit trail and human-in-the-loop features are not optional enhancements — they are the minimum bar for a tool used by SFC-licensed advisers. The "draft for review" framing must be explicit in the UI, not just implied.

---

## Sources

- SFC Circular 24EC55 (Nov 2024): https://apps.sfc.hk/edistributionWeb/api/circular/openFile?lang=EN&refNo=24EC55
- Clifford Chance SFC AI analysis: https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2024/11/sfc-circular-to-licensed-corporations-on-use-of-generative-ai.html
- Jump AI features (financial adviser meeting prep): https://jumpapp.com/products/meet/pre-meeting-prep
- Zocks document intelligence: https://www.zocks.io/features
- AI financial agents hallucination guardrails (DEV Community): https://dev.to/olivier-coreprose/ai-financial-agents-hallucinating-with-real-money-how-to-build-brokerage-grade-guardrails-af5
- Fabrication risk in regulated industries (Advisor360°): https://medium.com/advisor360-com/the-lie-that-looks-like-a-fact-fabrication-risk-in-ai-for-regulated-industries-11aea6a2c655
- Building regulator-defensible RAG systems: https://horkan.com/2026/01/02/building-regulator-defensible-enterprise-rag-systems-fca-pra-smcr
- Telegram compliance landscape: https://www.leapxpert.com/navigating-telegrams-current-regulatory-compliance-landscape-after-ceos-arrest/
- ESMA letter to Telegram on financial advertisements: https://www.esma.europa.eu/document/letter-telegram-preventing-online-harm-unauthorised-financial-advertisements
- Workmate RBAC for AI assistants: https://www.workmate.com/blog/designing-access-controls-and-rbac-for-ai-assistants
- 6 mistakes to avoid with AI for financial advisors: https://aldeninvestmentgroup.com/blog/6-mistakes-to-avoid-when-using-ai-for-financial-advisors/
