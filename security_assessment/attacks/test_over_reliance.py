"""
OVER-RELIANCE ON GENERATED OUTPUTS
===================================
Demonstrates the absence of safeguards that would prevent advisers from
treating AI-generated content as authoritative without verification.

Vulnerabilities tested:
- OR-1: No disclaimer on outputs
- OR-2: No document freshness/staleness indicator
- OR-3: No feedback mechanism for incorrect answers
- OR-4: No confidence scoring
"""

import pytest
from unittest.mock import MagicMock

from backend.schemas.query import QueryResponse


class TestNoDisclaimer:
    """OR-1: Generated answers carry no AI-generated disclaimer."""

    def test_response_schema_has_no_disclaimer_field(self):
        """QueryResponse has no disclaimer or warning field."""
        fields = QueryResponse.model_fields

        # VULNERABILITY: No mechanism to attach disclaimers
        assert "disclaimer" not in fields
        assert "warning" not in fields
        assert "ai_generated" not in fields

    def test_generation_prompt_has_no_disclaimer_instruction(self):
        """The system prompt does not instruct the LLM to add disclaimers."""
        from backend.services.generation_service import GENERATION_PROMPT

        # VULNERABILITY: No instruction to include caveats or disclaimers
        assert "disclaimer" not in GENERATION_PROMPT.lower()
        assert "not financial advice" not in GENERATION_PROMPT.lower()
        assert "verify" not in GENERATION_PROMPT.lower()


class TestNoFreshnessIndicator:
    """OR-2: No staleness warning when source documents are outdated."""

    def test_source_citation_has_no_date(self):
        """SourceCitation schema has no document_date or last_updated field."""
        from backend.schemas.query import SourceCitation

        fields = SourceCitation.model_fields
        # VULNERABILITY: Adviser cannot tell if source is current or years old
        assert "document_date" not in fields
        assert "last_updated" not in fields
        assert "ingested_at" not in fields

    def test_chunk_payload_has_no_staleness_check(self):
        """Vector store payload has no expiry or freshness metadata used at query time."""
        from backend.repositories.vector_repo import upsert_chunks

        # The payload_base dict passed to upsert_chunks has no TTL or date field
        # that would be checked during retrieval
        import inspect
        source = inspect.getsource(upsert_chunks)
        assert "expires_at" not in source
        assert "stale" not in source


class TestNoConfidenceScoring:
    """OR-4: No confidence score is provided to help advisers gauge reliability."""

    def test_response_has_no_confidence_field(self):
        """QueryResponse does not include a confidence or certainty score."""
        fields = QueryResponse.model_fields

        # VULNERABILITY: Adviser cannot distinguish high vs low confidence answers
        assert "confidence" not in fields
        assert "certainty" not in fields
        assert "relevance_score" not in fields

    def test_rerank_scores_not_propagated(self):
        """Rerank relevance scores are discarded — not passed to the response."""
        from backend.services.query_service import process_query
        import inspect

        source = inspect.getsource(process_query)
        # Rerank returns scored results but scores are not included in final output
        assert "relevance_score" not in source.split("# 10. Return")[1] if "# 10. Return" in source else True


class TestNoFeedbackMechanism:
    """OR-3: No way for advisers to flag incorrect or misleading answers."""

    def test_no_feedback_endpoint(self):
        """No API endpoint exists for submitting feedback on answers."""
        from backend.main import app

        paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                paths.append(route.path)

        # VULNERABILITY: No feedback loop for continuous improvement
        assert "/api/v1/feedback" not in paths
        assert "/api/v1/query/feedback" not in paths
        assert "/api/v1/report" not in paths

    def test_no_feedback_model(self):
        """No database model for storing user feedback on generated answers."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            from backend.models.feedback import Feedback  # noqa: F401
