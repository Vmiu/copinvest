"""
run_all_attacks.py
==================
Master script — runs all attacks against the live server in sequence.

Usage:
    python security_assessment/run_all_attacks.py
    python security_assessment/run_all_attacks.py <adviser_token>

The server must be running:
    python -m uvicorn backend.main:app --reload
"""

import subprocess
import sys
import httpx

BASE_URL = "http://localhost:8000"
PYTHON = sys.executable

ATTACKS = [
    ("01 — JWT Token Forgery",        "security_assessment/attacks/attack_01_token_forgery.py"),
    ("02 — Prompt Injection",         "security_assessment/attacks/attack_02_prompt_injection.py"),
    ("03 — Error Message Leakage",    "security_assessment/attacks/attack_03_error_leakage.py"),
    ("04 — Bulk Knowledge Extraction","security_assessment/attacks/attack_04_bulk_extraction.py"),
]


def check_server():
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def main():
    print("\n" + "█" * 60)
    print("  CopInvest — Live Security Attack Suite")
    print("█" * 60)

    if not check_server():
        print(f"\n[!] Server not reachable at {BASE_URL}")
        print("    Start it with: python -m uvicorn backend.main:app --reload")
        sys.exit(1)

    print(f"\n[✓] Server is up at {BASE_URL}\n")

    token_arg = sys.argv[1] if len(sys.argv) > 1 else None

    for name, script in ATTACKS:
        print("\n" + "─" * 60)
        print(f"  Running: {name}")
        print("─" * 60)
        cmd = [PYTHON, script]
        if token_arg:
            cmd.append(token_arg)
        subprocess.run(cmd)

    print("\n" + "█" * 60)
    print("  All attacks complete. See security_assessment/README.md")
    print("  for the full vulnerability report and recommended controls.")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    main()
