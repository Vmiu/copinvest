# Phase 1: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the conversation.

**Date:** 2026-04-29
**Phase:** 01-Data Foundation
**Mode:** discuss (interactive)
**Areas discussed:** Infrastructure setup, RBAC design, Audit trail mechanics

## Questions & Answers

### Infrastructure Setup

| Question | Options Presented | User Selection | Notes |
|----------|-------------------|----------------|-------|
| Database for local dev | SQLite / PostgreSQL via Docker | SQLite for dev | User prefers simpler setup |
| Vector store choice | Qdrant / ChromaDB / FAISS | Asked about Pinecone & Milvus | User wanted to understand alternatives |
| Vector store (round 2) | Qdrant / Pinecone / Milvus | Qdrant | After comparing data residency and pre-filtering |
| Qdrant deployment | In-process / Docker container | (Decided as Docker alongside Qdrant choice) | |

### RBAC Design

| Question | Options Presented | User Selection | Notes |
|----------|-------------------|----------------|-------|
| Role model | Fixed roles / Configurable roles | Fixed roles | 3 roles sufficient for prototype |
| Tier mapping | Strict hierarchy / Broader access | Strict hierarchy | adviser=Public, senior=Pub+Int+Restr, compliance=All |
| User creation | Seed file / Admin API / Self-registration | Seed file | No registration UI needed for prototype |

### Audit Trail Mechanics

| Question | Options Presented | User Selection | Notes |
|----------|-------------------|----------------|-------|
| Audit record timing | Progressive / Write-once + action record | Progressive | Record created at query, updated through lifecycle |
| Session definition | Inactivity timeout / Per-channel / Per-query | Inactivity timeout (30 min) | Sessions group audit records with start/end DateTime |

## Deferred Ideas

None.
