import random

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.repositories.vector_repo import (
    get_qdrant_client,
    query_with_rbac,
    setup_collection,
)

# Reproducible random vectors
random.seed(42)


def _random_vector(dim: int = 1024) -> list[float]:
    return [random.random() for _ in range(dim)]


# Pre-generate vectors so each point has a stable vector across tests
_VECTORS = [_random_vector() for _ in range(4)]
_QUERY_VECTOR = _random_vector()


@pytest.fixture
def qdrant_client() -> QdrantClient:
    """In-memory Qdrant with test collection seeded per D-05 role-tier mapping."""
    client = QdrantClient(":memory:")
    setup_collection(client, "test_docs")

    # Seed points per D-05:
    # tier 1 (public): adviser, senior_adviser, admin
    # tier 2 (internal): senior_adviser, admin
    # tier 3 (restricted): senior_adviser, admin
    # tier 4 (confidential): admin only
    client.upsert(
        collection_name="test_docs",
        points=[
            PointStruct(
                id=1,
                vector=_VECTORS[0],
                payload={
                    "sensitivity_tier": 1,
                    "allowed_roles": ["adviser", "senior_adviser", "admin"],
                    "text": "public doc",
                },
            ),
            PointStruct(
                id=2,
                vector=_VECTORS[1],
                payload={
                    "sensitivity_tier": 2,
                    "allowed_roles": ["senior_adviser", "admin"],
                    "text": "internal doc",
                },
            ),
            PointStruct(
                id=3,
                vector=_VECTORS[2],
                payload={
                    "sensitivity_tier": 3,
                    "allowed_roles": ["senior_adviser", "admin"],
                    "text": "restricted doc",
                },
            ),
            PointStruct(
                id=4,
                vector=_VECTORS[3],
                payload={
                    "sensitivity_tier": 4,
                    "allowed_roles": ["admin"],
                    "text": "confidential doc",
                },
            ),
        ],
    )
    return client


@pytest.fixture
def qdrant_client_restricted_only() -> QdrantClient:
    """In-memory Qdrant with only restricted/confidential points (no adviser access)."""
    client = QdrantClient(":memory:")
    setup_collection(client, "restricted_only")

    client.upsert(
        collection_name="restricted_only",
        points=[
            PointStruct(
                id=1,
                vector=_VECTORS[2],
                payload={
                    "sensitivity_tier": 3,
                    "allowed_roles": ["senior_adviser", "admin"],
                    "text": "restricted doc",
                },
            ),
            PointStruct(
                id=2,
                vector=_VECTORS[3],
                payload={
                    "sensitivity_tier": 4,
                    "allowed_roles": ["admin"],
                    "text": "confidential doc",
                },
            ),
        ],
    )
    return client


def test_setup_collection(qdrant_client: QdrantClient):
    """Collection is created and exists after setup."""
    assert qdrant_client.collection_exists("test_docs")


def test_rbac_filter_adviser(qdrant_client: QdrantClient):
    """Adviser role query returns only public (tier 1) points."""
    results = query_with_rbac(qdrant_client, _QUERY_VECTOR, "adviser", "test_docs")
    tiers = [p.payload["sensitivity_tier"] for p in results.points]
    assert len(results.points) == 1
    assert all(t == 1 for t in tiers)


def test_rbac_filter_senior(qdrant_client: QdrantClient):
    """Senior adviser query returns tiers 1-3."""
    results = query_with_rbac(
        qdrant_client, _QUERY_VECTOR, "senior_adviser", "test_docs"
    )
    tiers = {p.payload["sensitivity_tier"] for p in results.points}
    assert len(results.points) == 3
    assert tiers == {1, 2, 3}


def test_rbac_filter_admin(qdrant_client: QdrantClient):
    """Admin query returns all tiers (1-4)."""
    results = query_with_rbac(
        qdrant_client, _QUERY_VECTOR, "admin", "test_docs"
    )
    assert len(results.points) == 4


def test_adviser_blocked(qdrant_client_restricted_only: QdrantClient):
    """Adviser gets zero results when only restricted/confidential points exist (AUTH-05)."""
    results = query_with_rbac(
        qdrant_client_restricted_only, _QUERY_VECTOR, "adviser", "restricted_only"
    )
    assert len(results.points) == 0
