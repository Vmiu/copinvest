# CopInvest — External Penetration Test Report

**Date:** 2025-05-11
**Attacker system:** Separate machine on the same network (no shared filesystem, no shared credentials)
**Target system:** `http://<target-ip>:8000` — CopInvest bank investment chatbot API
**Method:** Pure black-box attack — the attacker system has ZERO access to the target's source code, `.env`, database, or project files
**Engagement type:** External adversary simulation

---

## Separation of Systems

| | Attacker System | Target System (CopInvest) |
|--|-----------------|---------------------------|
| **Role** | Penetration testing rig | Bank investment chatbot API |
| **Access** | Network only (HTTP to target port 8000) | Runs the FastAPI/uvicorn application |
| **Knowledge** | Only what the target exposes over HTTP | Full application stack |
| **Filesystem** | Contains only the attack test scripts | Contains source code, `.env`, database |
| **Credentials** | None initially — must be cracked via attacks | Stores hashed passwords in SQLite |

> **Key assumption:** The attacker system is a completely independent machine.
> It shares NO filesystem, NO environment variables, NO database, and NO source code
> with the CopInvest chatbot project. The only link is a TCP connection to port 8000.

---

## Running the Attacks from the Attacker System

The attack scripts are self-contained and require only `httpx` and `pytest`.
They do NOT import any CopInvest application code.

```bash
# From the attacker machine — point at the target's IP
TARGET_URL=http://<target-ip>:8000 pytest tests/test_attack_simulation.py -v

# After cracking credentials via ATK-03+04+20:
TARGET_URL=http://<target-ip>:8000 \
KNOWN_EMAIL=carol@copinvest.hk KNOWN_PASSWORD=compliance123 \
ADVISER_EMAIL=alice@copinvest.hk ADVISER_PASSWORD=adviser123 \
    pytest tests/test_attack_simulation.py -v
```

On Windows (attacker machine):
```cmd
set TARGET_URL=http://<target-ip>:8000
set KNOWN_EMAIL=carol@copinvest.hk
set KNOWN_PASSWORD=compliance123
set ADVISER_EMAIL=alice@copinvest.hk
set ADVISER_PASSWORD=adviser123
uv run pytest tests/test_attack_simulation.py -v
```

---

## Threat Model

```
┌─────────────────────┐         HTTP/TCP          ┌─────────────────────────┐
│   ATTACKER SYSTEM   │ ──────────────────────── → │   TARGET: CopInvest     │
│                     │                            │   (Bank Chatbot API)    │
│  • pytest scripts   │   Only port 8000 open      │  • FastAPI + uvicorn    │
│  • httpx client     │   No SSH, no file share    │  • SQLite database      │
│  • No source code   │                            │  • .env with secrets    │
│  • No .env access   │                            │  • Qdrant vector DB     │
└─────────────────────┘                            └─────────────────────────┘
```

The attacker has:
- ✅ Network access to the target API (port 8000)
- ❌ No access to source code or repository
- ❌ No access to `.env` or secret keys
- ❌ No access to the database
- ❌ No access to server logs
- ❌ No knowledge of internal architecture (until discovered via ATK-01)

---

## Test Results (Live Run)

```
50 tests collected

--- Round 1 ---
FAILED  ATK-01  OpenAPI schema publicly accessible
PASSED  ATK-02  SQL injection blocked (11 payloads)
FAILED  ATK-03  Brute force — 20 attempts, zero lockout
FAILED  ATK-04  Timing side-channel — 58.6x ratio
PASSED  ATK-05  Forged JWT rejected (6 weak secrets tried)
PASSED  ATK-06  JWT alg=none bypass rejected (4 case variants)
PASSED  ATK-07  Expired token rejected
PASSED  ATK-08  HTTP verb tampering blocked (3 methods)
PASSED  ATK-09  No token rejected
SKIPPED ATK-10  Privilege escalation (no adviser creds set)
PASSED  ATK-11  Path traversal filename — properly rejected (422)
PASSED  ATK-12  Sensitivity tier out of range rejected
FAILED  ATK-13  Server fingerprinting — server: uvicorn

--- Round 2 ---
FAILED  ATK-14  Large file 11MB — HTTP 422 instead of 413
PASSED  ATK-15  Empty file rejected (400)
PASSED  ATK-16a MIME spoof malware.exe — rejected (422)
PASSED  ATK-16b MIME spoof script.js — rejected (422)
PASSED  ATK-16c MIME spoof report.pdf.exe — rejected (422)
FAILED  ATK-17  Concurrent flood 50 requests — no limiting
PASSED  ATK-18a–18e  Malformed JWT variants — all rejected
PASSED  ATK-19a Long username (10k) rejected
FAILED  ATK-19b Long password 100k — HTTP 500, unauthenticated DoS
FAILED  ATK-20  Password spray — 2 accounts cracked!

--- Round 3 ---
PASSED  ATK-22  Host header injection — not reflected
PASSED  ATK-23a–m  document_id injection (13 variants) — all rejected (422)
PASSED  ATK-25  Null byte in filename — rejected (422)
PASSED  ATK-27  Float tier '1.0' — rejected (422)
FAILED  ATK-28  No token revocation — old tokens valid after re-login

10 failed, 39 passed, 1 skipped in 39.46s
```

---

## Summary

### Round 1

| ID | Attack | Auth Required | Result | Severity |
|----|--------|---------------|--------|----------|
| ATK-01 | OpenAPI schema exposed without auth | None | 💀 Exploited | Medium |
| ATK-02 | SQL injection in login (11 payloads) | None | ✅ Blocked | — |
| ATK-03 | Brute force — no lockout (20 attempts) | None | 💀 Exploited | High |
| ATK-04 | Email enumeration via timing (58.6x) | None | 💀 Exploited | High |
| ATK-05 | Forged JWT (6 weak secrets tried) | None | ✅ Blocked | — |
| ATK-06 | JWT alg=none bypass (4 case variants) | None | ✅ Blocked | — |
| ATK-07 | Expired token replay | None | ✅ Blocked | — |
| ATK-08 | HTTP verb tampering | None | ✅ Blocked | — |
| ATK-09 | No token on protected endpoint | None | ✅ Blocked | — |
| ATK-10 | Privilege escalation (adviser → compliance) | Adviser creds | ⏭️ Skipped | — |
| ATK-11 | Path traversal in upload filename | Compliance creds | ✅ Blocked (422) | — |
| ATK-12 | Sensitivity tier out of range | Compliance creds | ✅ Blocked | — |
| ATK-13 | Server fingerprinting via headers | None | 💀 Exposed | Low |

### Round 2

| ID | Attack | Auth Required | Result | Severity |
|----|--------|---------------|--------|----------|
| ATK-14 | Large file upload 11MB | Compliance creds | ⚠️ Wrong status (422 not 413) | Low |
| ATK-15 | Empty file upload | Compliance creds | ✅ Blocked (400) | — |
| ATK-16a | MIME spoof — .exe as PDF | Compliance creds | ✅ Blocked (422) | — |
| ATK-16b | MIME spoof — .js as PDF | Compliance creds | ✅ Blocked (422) | — |
| ATK-16c | MIME spoof — .pdf.exe as PDF | Compliance creds | ✅ Blocked (422) | — |
| ATK-17 | Concurrent flood — 50 parallel logins | None | 💀 No limiting | Medium |
| ATK-18a–e | Malformed JWT variants (5 types) | None | ✅ All blocked (401) | — |
| ATK-19a | Long username (10,000 chars) | None | ✅ Blocked (401) | — |
| ATK-19b | Long password (100,000 chars) | None | 💀 Server crash (500) | Critical |
| ATK-20 | Password spray (17 passwords × 3 users) | None | 💀 2 accounts cracked | Critical |

### Round 3

| ID | Attack | Auth Required | Result | Severity |
|----|--------|---------------|--------|----------|
| ATK-22 | Host header injection (3 variants) | None | ✅ Not reflected | — |
| ATK-23a–m | document_id injection (13 variants) | Compliance creds | ✅ All blocked (422) | — |
| ATK-25 | Null byte in filename | Compliance creds | ✅ Blocked (422) | — |
| ATK-27 | Float tier '1.0' — enum handling | Compliance creds | ✅ Blocked (422) | — |
| ATK-28 | No token revocation after re-login | None (valid token) | 💀 Old token still valid | High |

---

## Black-Box Attack Chain (from attacker system)

```
┌─ Attacker System ─────────────────────────────────────────────────────────┐
│                                                                           │
│  Step 1 — Reconnaissance (ATK-01)                                         │
│    GET /openapi.json  →  full API map, all endpoints, all schemas         │
│    No auth required. Target reveals its entire attack surface.            │
│    Attacker learns role names: "adviser", "compliance"                    │
│                                                                           │
│  Step 2 — Email enumeration (ATK-04)                                      │
│    POST /api/v1/auth/token  →  timing side-channel                        │
│    carol@copinvest.hk = 186ms  vs  nobody@fake.hk = 3ms  →  58.6x ratio  │
│    Attacker confirms valid email addresses without any credentials.       │
│                                                                           │
│  Step 3 — Password spray (ATK-20)                                         │
│    Attacker derives passwords from role names found in ATK-01:            │
│    "compliance123", "adviser123" — both CRACKED on first attempt.         │
│    No rate limiting (ATK-03) means unlimited spray attempts.              │
│                                                                           │
│  Step 4 — Full authenticated access                                       │
│    carol@copinvest.hk:compliance123  →  compliance role (full ingest)     │
│    alice@copinvest.hk:adviser123     →  adviser role                      │
│                                                                           │
│  Step 5 — Denial of service (ATK-19b)                                     │
│    POST /api/v1/auth/token  password=AAAA...(100k chars)  →  HTTP 500     │
│    Zero auth required. One request crashes the login endpoint.            │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Confirmed Vulnerabilities

> All exploits below were executed from the attacker system with NO access
> to the target's source code, configuration, or filesystem.

### 💀 ATK-01 — Full API map exposed without authentication

**Endpoint:** `GET /openapi.json`
**Auth required:** None
**Severity:** Medium

**Live result:**
```
GET http://<target-ip>:8000/openapi.json  →  HTTP 200
Endpoints exposed: /api/v1/auth/token, /api/v1/auth/me, /api/v1/ingest, /health
```

**Impact:** Attacker gains complete knowledge of the target's API surface, parameter names, data types, role names, and security schemes — equivalent to reading the source code's route definitions.

---

### 💀 ATK-03 — Unlimited brute force on login endpoint

**Endpoint:** `POST /api/v1/auth/token`
**Auth required:** None
**Severity:** High

**Live result:** 20 rapid requests, all returned 401, zero rate limiting applied.

**Impact:** Attacker can run unlimited password attempts from their machine. Combined with ATK-04 and ATK-20, credential compromise is trivial.

---

### 💀 ATK-04 — Email enumeration via timing side-channel (58.6x ratio)

**Endpoint:** `POST /api/v1/auth/token`
**Auth required:** None
**Severity:** High

**Live result (median over 10 interleaved samples):**
```
carol@copinvest.hk   -> 185.9ms  ← VALID ACCOUNT (bcrypt runs)
nonexistent@nowhere  ->   3.2ms  ← does not exist (no bcrypt)
Ratio: 58.6x
```

**Impact:** Attacker enumerates all valid email addresses remotely. The timing difference is so large (58x) that even network jitter cannot mask it. ~10 requests per email is sufficient for confident classification.

---

### 💀 ATK-13 — Server technology disclosed in response headers

**Endpoint:** Any
**Auth required:** None
**Severity:** Low

**Live result:** Every response includes `server: uvicorn` — attacker knows exact server software and can target known uvicorn/Starlette CVEs.

---

### 💀 ATK-17 — No concurrent request limiting

**Endpoint:** `POST /api/v1/auth/token`
**Auth required:** None
**Severity:** Medium

**Live result:**
```
50 parallel requests  →  {401: 50}  (9,233ms total, ~5 req/s)
No 429, no 503, no connection refused
```

**Impact:** Attacker can flood the login endpoint from multiple threads/IPs with zero resistance. Combined with ATK-03, enables high-speed brute force.

---

### 💀 ATK-19b — 100,000 character password crashes target (unauthenticated DoS)

**Endpoint:** `POST /api/v1/auth/token`
**Auth required:** None — zero authentication required
**Severity:** Critical

**Live result:**
```
POST http://<target-ip>:8000/api/v1/auth/token
password=AAAA...(100,000 chars)  →  HTTP 500
```

**Root cause:** bcrypt has a maximum input length (72 bytes). The server passes the full 100k string to the password hasher without length validation, causing an internal error.

**Impact:** Any anonymous user on the network can crash the banking chatbot's authentication endpoint with a single HTTP request. This is a zero-auth, zero-knowledge denial of service.

---

### 💀 ATK-20 — Password spray cracked 2 accounts

**Endpoint:** `POST /api/v1/auth/token`
**Auth required:** None
**Severity:** Critical

**Live result:**
```
carol@copinvest.hk:compliance123  →  HTTP 200  ← CRACKED
alice@copinvest.hk:adviser123     →  HTTP 200  ← CRACKED
```

**Attack method:** Attacker derived password guesses from role names exposed in ATK-01's OpenAPI schema (`"compliance"` → `"compliance123"`, `"adviser"` → `"adviser123"`). No rate limiting (ATK-03) allowed unlimited attempts.

**Impact:** Full account compromise of a compliance officer and an adviser. The compliance account has unrestricted document ingestion access. Passwords follow a trivially guessable `{role}123` pattern — violates HKMA TM-E-1 password complexity requirements for banking systems.

---

### 💀 ATK-28 — No token revocation — stolen tokens valid for 24 hours

**Endpoint:** `GET /api/v1/auth/me`
**Auth required:** Any valid token
**Severity:** High

**Live result:**
```
Old token (session 1)  →  HTTP 200  {"user_id":"user-003","role":"compliance"}
New token (session 2)  →  HTTP 200  {"user_id":"user-003","role":"compliance"}
Both tokens valid simultaneously — no revocation mechanism exists
```

**Impact:** Tokens are stateless JWTs with no server-side revocation. If an attacker intercepts a token (e.g. via network sniffing or XSS), it remains valid for the full 24-hour expiry window. There is no logout, no session invalidation, and no way to revoke a compromised token without rotating the secret key (which kills ALL sessions).

---

## What Was Blocked ✅

| Attack | Defence |
|--------|---------|
| SQL injection in login (11 payloads) | Parameterised queries (ORM) |
| Forged JWT with 6 weak secrets | Strong secret key + signature verification |
| JWT `alg=none` bypass (4 case variants) | Library rejects unsigned tokens |
| Expired token replay | Expiry check enforced |
| Path traversal in filename | Input validation rejects traversal sequences |
| MIME type spoofing (3 variants) | PDF content validation — non-PDF rejected |
| document_id injection (13 variants) | Proper error handling — returns 422 |
| Null byte in filename | Input validation catches null bytes |
| Float sensitivity tier | Enum validation rejects non-integer |
| Sensitivity tier out of range | Pydantic enum validation |
| HTTP verb tampering | Route method enforcement |
| Empty file upload | Explicit content check |
| Malformed JWT (5 variants) | Token parsing rejects all |
| Long username (10k chars) | DB query returns None cleanly |
| Host header injection (3 variants) | Not reflected in response |

---

## What Would Require Access to the Target System (Not Black-Box)

| Attack | Why it cannot be done from the attacker system |
|--------|------------------------------------------------|
| SECRET_KEY forgery | Key exists only in target's `.env` file — not readable over the network |
| Ghost user JWT impersonation | Requires the secret key to forge a valid signature |
| Database manipulation | SQLite file is on target's filesystem — no remote access |
| Log poisoning | Server logs are on target's filesystem |

> **Warning:** If the target's repository is ever made public, or the secret key
> leaks through error messages or logs, the attacker system can immediately
> escalate to full token forgery without needing filesystem access.

---

## Attacker System Requirements

The attack scripts are designed to run from any machine with Python 3.11+ and network access to the target. No CopInvest source code is needed.

**Dependencies (attacker machine only):**
```
httpx
pytest
pytest-asyncio
```

**What the attacker system does NOT have:**
- No copy of the CopInvest repository
- No access to `backend/`, `alembic/`, or any application code
- No `.env` file or secret keys
- No database access
- No knowledge of internal implementation until discovered via ATK-01/ATK-13

---

## Vulnerability Summary

| # | Vulnerability | Severity | Auth Required | Remediation |
|---|---------------|----------|---------------|-------------|
| 1 | Weak passwords (`{role}123` pattern) — ATK-20 | Critical | None | Enforce password complexity policy, rotate all passwords |
| 2 | Unauthenticated DoS via 100k password — ATK-19b | Critical | None | Reject passwords > 72 chars before bcrypt |
| 3 | No rate limiting on login — ATK-03 | High | None | Add rate limiting (e.g. 5 failures per minute per IP) |
| 4 | Timing side-channel (58.6x) — ATK-04 | High | None | Add constant-time fake bcrypt for non-existent users |
| 5 | No token revocation — ATK-28 | High | Valid token | Implement token blacklist or short-lived tokens + refresh |
| 6 | No concurrent request limiting — ATK-17 | Medium | None | Add connection/request rate limiting middleware |
| 7 | OpenAPI schema publicly accessible — ATK-01 | Medium | None | Require auth for /openapi.json or disable in production |
| 8 | Server header fingerprinting — ATK-13 | Low | None | Remove or override `server` response header |

**Total: 8 real vulnerabilities (2 Critical, 3 High, 2 Medium, 1 Low)**

---

## 8 Vulnerabilities Remain Open

ATK-01, ATK-03, ATK-04, ATK-13, ATK-17, ATK-19b, ATK-20, ATK-28

All exploitable remotely from the attacker system with no target filesystem access.
