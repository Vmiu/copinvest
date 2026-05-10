"""
HALLUCINATION ATTACKS
=====================
Demonstrates scenarios where the system can produce fabricated or unsupported
information despite the "only use context" instruction.

Vulnerabilities tested:
- H-1: Citation markers are not verified against chunk content
- H-2: Query rewrite semantic drift causes irrelevant retrieval
- H-3: No confidence threshold — low-relevance chunks still generate answers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.generation_service import generate_answer, _extract_sources


class TestUnverifiedCitations:
    """H-1: The system trusts [N] markers without checking that chunk N
    actually supports the claim made."""

    @pytest.mark.asyncio
    async def test_fabricated_citation(self):
        """LLM can cite chunk [1] while making a claim not present in that chunk."""
        chunk = MagicMock()
        chunk.payload = {
            "source_id": "product-sheet.pdf",
            "section_title": "Risk Factors",
            "chunk_index": 3,
            "text": "This fund invests primarily in Asia-Pacific equities.",
        }

        # LLM fabricates a specific return figure and cites chunk [1]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "The fund returned 23.5% in 2024 [1], outperforming its benchmark."
        )
        mock_response.usage.prompt_tokens = 150
        mock_response.usage.completion_tokens = 20

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_answer("What was the fund return?", [chunk], mock_client)

        # System accepts the answer with citation — no verification that
        # "23.5% in 2024" actually appears in chunk text
        assert result["answer"] == "The fund returned 23.5% in 2024 [1], outperforming its benchmark."
        assert result["not_found"] is False
        assert len(result["sources"]) == 1

        # VULNERABILITY: The cited chunk says nothing about 23.5% returns
        assert "23.5%" not in chunk.payload["text"]

    def test_extract_sources_does_not_validate_content(self):
        """_extract_sources only checks index bounds, not semantic match."""
        chunk = MagicMock()
        chunk.payload = {
            "source_id": "doc.pdf",
            "section_title": "Overview",
            "chunk_index": 0,
            "text": "General company overview.",
        }

        # Answer claims something completely unrelated to the chunk
        answer = "The CEO resigned in March 2024 [1]"
        sources = _extract_sources(answer, [chunk])

        # Source is returned despite the chunk containing no resignation info
        assert len(sources) == 1
        assert sources[0]["doc_name"] == "doc.pdf"


class TestNoConfidenceThreshold:
    """H-3: The system generates answers even when reranked chunks have
    marginal relevance, with no confidence indicator to the user."""

    @pytest.mark.asyncio
    async def test_answer_generated_from_single_weak_chunk(self):
        """Even one barely-relevant chunk triggers full answer generation."""
        # A chunk that is tangentially related at best
        weak_chunk = MagicMock()
        weak_chunk.payload = {
            "source_id": "newsletter-q1.pdf",
            "section_title": "Market Commentary",
            "chunk_index": 12,
            "text": "Markets experienced volatility in Q1 due to geopolitical tensions.",
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "Based on the available information, the recommended portfolio allocation "
            "for conservative clients is 60% bonds and 40% equities [1]."
        )
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 30

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await generate_answer(
            "What is the recommended allocation for conservative clients?",
            [weak_chunk],
            mock_client,
        )

        # System returns a specific allocation recommendation from a chunk
        # that only mentions "volatility" — no confidence warning
        assert "60% bonds" in result["answer"]
        assert result["not_found"] is False
        # VULNERABILITY: No confidence score, no staleness warning, no disclaimer


class TestQueryRewriteDrift:
    """H-2: Semantic drift in query rewrite causes retrieval of irrelevant chunks,
    leading to hallucinated answers grounded in wrong context."""

    @pytest.mark.asyncio
    async def test_rewrite_changes_intent(self):
        """Rewrite can transform a simple query into something with different meaning."""
        from backend.services.query_rewrite_service import rewrite_query

        original = "What's the fee?"

        # Mock: rewrite expands to something overly specific and wrong
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "What is the annual management fee percentage for the flagship "
            "global macro hedge fund product?"
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        rewritten = await rewrite_query(original, mock_client)

        # The user asked about "the fee" (could be advisory fee, platform fee, etc.)
        # but rewrite assumed hedge fund management fee — retrieval will be wrong
        assert "hedge fund" in rewritten
        assert rewritten != original
