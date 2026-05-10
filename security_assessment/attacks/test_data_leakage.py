"""
DATA LEAKAGE ATTACKS
====================
Demonstrates how sensitive information can be exposed through various channels.

Vulnerabilities tested:
- DL-1: Audit logs store full prompt (including all retrieved chunk text)
- DL-3: Error messages expose internal details
- DL-4: JWT tokens expose role and user_id in plaintext
- DL-5: No query rate limiting enables bulk knowledge extraction
"""

import base64
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.security import create_access_token, decode_access_token


class TestJWTDataExposure:
    """DL-4: JWT tokens contain plaintext user identity and role."""

    def test_token_payload_readable_without_key(self):
        """Anyone who intercepts the token can read user_id and role."""
        token = create_access_token({"sub": "user-secret-001", "role": "compliance"})

        # JWT is base64-encoded — no decryption needed to read payload
        payload_b64 = token.split(".")[1]
        # Add padding
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # VULNERABILITY: Identity and privilege level exposed in plaintext
        assert payload["sub"] == "user-secret-001"
        assert payload["role"] == "compliance"

    def test_no_token_encryption(self):
        """Token uses HS256 signing only — no encryption (JWE)."""
        token = create_access_token({"sub": "user-001", "role": "adviser"})

        # Header reveals algorithm
        header_b64 = token.split(".")[0]
        header_b64 += "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header["alg"] == "HS256"  # Signing only, not encrypting
        assert header.get("enc") is None  # No encryption algorithm


class TestAuditLogLeakage:
    """DL-1: The audit log stores the full prompt_sent field, which contains
    all retrieved chunk text — including confidential tier content."""

    @pytest.mark.asyncio
    async def test_prompt_sent_contains_chunk_text(self):
        """The prompt stored in audit includes full text of retrieved chunks."""
        from backend.services.generation_service import generate_answer

        confidential_chunk = MagicMock()
        confidential_chunk.payload = {
            "source_id": "merger-plan.pdf",
            "section_title": "Target Valuation",
            "chunk_index": 0,
            "sensitivity_tier": 4,  # Confidential — compliance only
            "text": "Target acquisition price: HKD 4.2 billion. Board approved 2024-03-15.",
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The target price is HKD 4.2 billion [1]"
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 15

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_answer("What is the acquisition price?", [confidential_chunk], mock_client)

        # VULNERABILITY: prompt_sent contains the full confidential text
        # This gets stored in audit_log.prompt_sent (see query_service.py line ~70)
        assert "HKD 4.2 billion" in result["prompt_sent"]
        assert "Board approved" in result["prompt_sent"]


class TestErrorMessageLeakage:
    """DL-3: Internal error details are passed to HTTP responses."""

    @pytest.mark.asyncio
    async def test_runtime_error_exposes_internals(self, client):
        """RuntimeError messages are returned verbatim to the client."""
        from backend.core.dependencies import get_generation_client, get_chunking_client, get_qdrant_client

        # Simulate an internal error that leaks infrastructure details
        def raise_error():
            raise RuntimeError(
                "Connection refused: qdrant://internal-qdrant.prod.svc:6333 "
                "collection='documents_confidential'"
            )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError(
            "Connection to https://api.deepseek.com failed: API key sk-abc123... invalid"
        ))

        app = client._transport.app  # noqa
        # This test demonstrates the pattern — the actual endpoint would expose the error


class TestBulkExtractionNoRateLimit:
    """DL-5: No rate limiting allows systematic extraction of the knowledge base."""

    def test_no_rate_limit_middleware(self):
        """Verify no rate limiting is configured on the query endpoint."""
        from backend.main import app

        # Check that no rate-limiting middleware is registered
        middleware_classes = [m.cls.__name__ for m in app.user_middleware if hasattr(m, 'cls')]

        # VULNERABILITY: No rate limiter present
        assert "RateLimitMiddleware" not in middleware_classes
        assert "SlowAPIMiddleware" not in middleware_classes

    def test_unlimited_queries_possible(self):
        """An authenticated user can make unlimited rapid queries — no throttle exists."""
        from backend.main import app

        # Collect all middleware class names
        middleware_names = []
        for m in app.user_middleware:
            cls = getattr(m, 'cls', None) or getattr(m, 'kwargs', {}).get('cls')
            if cls:
                middleware_names.append(cls.__name__)

        # VULNERABILITY: No rate-limiting middleware registered
        assert not any('rate' in n.lower() or 'throttle' in n.lower() or 'limit' in n.lower()
                       for n in middleware_names)
