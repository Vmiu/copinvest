# Security Assessment — CopInvest GenAI RAG System

## Executive Summary

This assessment evaluates the CopInvest system against five risk categories critical to GenAI deployments in financial services:

| Risk Category | Current Severity | Status |
|---|---|---|
| Hallucinations | **Medium** | Partially mitigated |
| Prompt Injection | **High** | Vulnerable |
| Data Leakage | **High** | Vulnerable |
| Weak Governance | **Medium** | Partially addressed |
| Over-reliance on Generated Outputs | **High** | No controls |

---

## 1. Hallucinations

### Current Mitigations
- System prompt instructs LLM to use "ONLY the provided context chunks"
- `NO_RELEVANT_CONTENT` fallback when context is insufficient
- Inline citation markers `[N]` link claims to source chunks

### Remaining Vulnerabilities

**H-1: No citation verification.** The system trusts the LLM's `[N]` markers without verifying that the cited chunk actually supports the claim. The LLM can hallucinate a fact and attach a citation to an unrelated chunk.

**H-2: Query rewrite can drift semantics.** The rewrite step (`query_rewrite_service.py`) transforms the user query before retrieval. If the rewrite drifts, the retrieved chunks may not match the user's intent, causing the LLM to confabulate an answer from irrelevant context.

**H-3: No confidence scoring.** The system returns answers without any confidence indicator. An adviser cannot distinguish a well-supported answer from one based on a single marginal chunk.

### Demonstration
See [`attacks/test_hallucination.py`](attacks/test_hallucination.py)

---

## 2. Prompt Injection

### Current Mitigations
- None. User query is inserted directly into the LLM prompt without sanitisation.

### Vulnerabilities

**PI-1: Direct injection via query field.** The user query is placed inside `<request>...</request>` tags in `generation_service.py`, but there is no escaping or validation. An attacker can close the tag and inject new instructions.

**PI-2: Indirect injection via document content.** A compliance officer could ingest a document containing adversarial instructions embedded in the text. When these chunks are retrieved, the LLM may follow the injected instructions instead of the system prompt.

**PI-3: Query rewrite amplification.** The rewrite service passes raw user input to DeepSeek. A crafted query can manipulate the rewrite to produce a completely different retrieval query, bypassing RBAC by retrieving chunks the user shouldn't contextually access.

### Demonstration
See [`attacks/test_prompt_injection.py`](attacks/test_prompt_injection.py)

---

## 3. Data Leakage

### Current Mitigations
- RBAC filter on Qdrant queries (`allowed_roles` field)
- Sensitivity tiers (1–4) mapped to roles

### Vulnerabilities

**DL-1: System prompt leakage.** The full system prompt and context are stored in `audit_log.prompt_sent`. If audit logs are accessible (e.g., via a future admin endpoint or database breach), all retrieved chunk text is exposed regardless of the querying user's tier.

**DL-2: Cross-session context bleed.** Session management (`session_service`) groups queries, but the generation service does not include conversation history. However, if conversation history is added later without tier filtering, a lower-tier user could reference content from a higher-tier chunk surfaced in a previous turn.

**DL-3: Error messages expose internals.** `RuntimeError` exceptions are passed directly to HTTP responses (`detail=str(e)`), potentially leaking internal paths, API keys in error messages, or Qdrant collection names.

**DL-4: Token in response headers.** JWT tokens contain `user_id` and `role` in plaintext (base64). If intercepted (no HTTPS enforcement in code), full identity is exposed.

**DL-5: Embedding model sees all tiers.** The Voyage AI API receives chunk text for embedding regardless of sensitivity tier — the third-party provider sees confidential content.

### Demonstration
See [`attacks/test_data_leakage.py`](attacks/test_data_leakage.py)

---

## 4. Weak Governance

### Current Mitigations
- Audit trail records every query (user, query text, response, model, tokens)
- Role-based access control (3 roles)
- Only `compliance` role can ingest documents

### Vulnerabilities

**WG-1: No human-in-the-loop for high-stakes outputs.** Generated meeting briefs and follow-up notes go directly to the adviser with no compliance review step.

**WG-2: No document versioning governance.** Re-ingestion with the same `document_id` silently replaces content. There is no approval workflow, diff review, or rollback capability.

**WG-3: No query rate limiting.** An authenticated user can make unlimited queries, enabling bulk extraction of the knowledge base.

**WG-4: No model output logging review.** Audit logs exist but there is no alerting, sampling, or periodic review process defined.

**WG-5: No data retention policy.** Audit logs grow indefinitely with no defined retention period, creating regulatory risk under PDPO (Hong Kong Personal Data Privacy Ordinance).

**WG-6: 24-hour token expiry is excessive.** `access_token_expire_minutes = 1440` means a stolen token is valid for a full day.

### Demonstration
See [`attacks/test_weak_governance.py`](attacks/test_weak_governance.py)

---

## 5. Over-reliance on Generated Outputs

### Current Mitigations
- None. No disclaimers, confidence scores, or mandatory human review.

### Vulnerabilities

**OR-1: No disclaimer on outputs.** Generated answers carry no warning that they are AI-generated and may contain errors. In a regulated financial context, this creates liability.

**OR-2: No "freshness" indicator.** Chunks may come from outdated documents. The system does not warn when source documents are stale.

**OR-3: Meeting briefs presented as authoritative.** An adviser may treat a generated brief as a complete summary, missing critical information not captured in the ingested documents.

**OR-4: No feedback loop.** There is no mechanism for advisers to flag incorrect answers, creating no path to improvement.

---

## Recommended Controls Before Deployment

| # | Control | Priority | Effort |
|---|---|---|---|
| 1 | Input sanitisation — strip/escape XML-like tags from user queries | Critical | Low |
| 2 | Output disclaimer: "AI-generated. Verify before use." on every response | Critical | Low |
| 3 | Rate limiting (e.g., 50 queries/hour per user) | High | Low |
| 4 | Reduce token expiry to 1 hour; add refresh token flow | High | Medium |
| 5 | Citation verification — check that cited chunk text supports the claim | High | High |
| 6 | Human review queue for follow-up notes before sending to clients | Critical | Medium |
| 7 | Document ingestion approval workflow (dual sign-off) | High | Medium |
| 8 | Confidence score based on rerank scores; suppress low-confidence answers | High | Medium |
| 9 | Audit log alerting — flag unusual query patterns | Medium | Medium |
| 10 | Data retention policy — auto-purge audit logs after 7 years (PDPO) | Medium | Low |
| 11 | HTTPS enforcement + HSTS headers | Critical | Low |
| 12 | Redact chunk text from audit logs or encrypt at rest | High | Medium |
| 13 | Content scanning on ingested documents for adversarial patterns | High | High |
| 14 | Staleness warning when source doc is >6 months old | Medium | Low |
| 15 | Feedback mechanism — thumbs up/down on answers | Medium | Low |

---

## How to Run the Attack Demonstrations

```bash
uv run pytest security_assessment/attacks/ -v
```

All tests use mocked LLM responses and in-memory databases — no API keys required.
