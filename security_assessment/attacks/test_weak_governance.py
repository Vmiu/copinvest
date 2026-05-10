"""
WEAK GOVERNANCE ATTACKS
=======================
Demonstrates governance gaps that would be unacceptable in a regulated
financial services environment (SFC-regulated in Hong Kong).

Vulnerabilities tested:
- WG-1: No human-in-the-loop for generated outputs
- WG-2: Silent document replacement with no approval workflow
- WG-3: Excessive token lifetime (24 hours)
- WG-4: No audit review or alerting mechanism
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

from backend.core.config import get_settings
from backend.core.security import create_access_token


class TestNoHumanInTheLoop:
    """WG-1: Generated meeting briefs and follow-up notes go directly to
    the adviser with no compliance review step."""

    def test_query_response_has_no_review_flag(self):
        """Response schema has no field for 'requires_review' or 'draft_status'."""
        from backend.schemas.query import QueryResponse

        fields = QueryResponse.model_fields
        # VULNERABILITY: No mechanism to flag outputs for human review
        assert "requires_review" not in fields
        assert "draft_status" not in fields
        assert "approved_by" not in fields
        assert "disclaimer" not in fields

    def test_no_review_queue_model(self):
        """No database model exists for a review/approval queue."""
        from backend.models import base
        import backend.models as models_pkg

        # Check that no ReviewQueue or ApprovalQueue model exists
        model_names = [name for name in dir(models_pkg) if not name.startswith("_")]
        assert "ReviewQueue" not in model_names
        assert "ApprovalQueue" not in model_names


class TestSilentDocumentReplacement:
    """WG-2: Re-ingestion with same document_id silently replaces content
    with no approval workflow, diff review, or rollback."""

    def test_ingest_endpoint_accepts_replacement_without_approval(self):
        """The ingest endpoint allows document_id parameter for replacement."""
        from backend.routers.ingest import ingest_document
        import inspect

        sig = inspect.signature(ingest_document)
        params = sig.parameters

        # document_id is accepted — enables silent replacement
        assert "document_id" in params

        # VULNERABILITY: No parameters for approval_id, reviewer, or reason
        assert "approval_id" not in params
        assert "reviewer_id" not in params
        assert "replacement_reason" not in params

    def test_no_document_version_history(self):
        """No model tracks previous versions of ingested documents."""
        from backend.models.document import DocumentRecord
        import inspect

        source = inspect.getsource(DocumentRecord)

        # VULNERABILITY: No version tracking fields
        assert "version" not in source
        assert "previous_id" not in source
        assert "replaced_by" not in source


class TestExcessiveTokenLifetime:
    """WG-3: 24-hour token expiry is excessive for a financial system."""

    def test_token_expiry_is_24_hours(self):
        """Default token lifetime is 1440 minutes (24 hours)."""
        settings = get_settings()
        assert settings.access_token_expire_minutes == 1440

        # VULNERABILITY: A stolen token is valid for an entire day
        # Financial systems typically use 15-60 minute tokens with refresh
        assert settings.access_token_expire_minutes > 60  # Proves it's excessive

    def test_no_refresh_token_mechanism(self):
        """No refresh token endpoint exists — only long-lived access tokens."""
        from backend.routers.auth import router

        paths = [route.path for route in router.routes if hasattr(route, 'path')]
        # VULNERABILITY: No refresh endpoint — forces long-lived tokens
        assert "/api/v1/auth/refresh" not in paths

    def test_no_token_revocation(self):
        """No mechanism to revoke a compromised token before expiry."""
        from backend.routers.auth import router

        paths = [route.path for route in router.routes if hasattr(route, 'path')]
        assert "/api/v1/auth/revoke" not in paths
        assert "/api/v1/auth/logout" not in paths


class TestNoAuditAlerting:
    """WG-4: Audit logs exist but have no review, alerting, or anomaly detection."""

    def test_no_alert_service(self):
        """No alerting service exists in the codebase."""
        import importlib
        with pytest.raises((ImportError, ModuleNotFoundError)):
            importlib.import_module("backend.services.alert_service")

    def test_audit_log_has_no_review_fields(self):
        """Audit records have no 'reviewed_by' or 'flagged' fields."""
        from backend.models.audit_log import AuditLog
        import inspect

        source = inspect.getsource(AuditLog)
        # VULNERABILITY: No mechanism to mark logs as reviewed or flag anomalies
        assert "reviewed_by" not in source
        assert "flagged" not in source
        assert "alert_sent" not in source
