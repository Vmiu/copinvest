from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    VectorParams,
)

from backend.core.config import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def setup_collection(
    client: QdrantClient, collection_name: str | None = None
) -> None:
    settings = get_settings()
    name = collection_name or settings.qdrant_collection

    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    # Ensure payload indexes exist (idempotent)
    client.create_payload_index(
        collection_name=name,
        field_name="allowed_roles",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="sensitivity_tier",
        field_schema=PayloadSchemaType.INTEGER,
    )


def query_with_rbac(
    client: QdrantClient,
    query_vector: list[float],
    user_role: str,
    collection: str | None = None,
    limit: int = 20,
):
    settings = get_settings()
    name = collection or settings.qdrant_collection

    return client.query_points(
        collection_name=name,
        query=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="allowed_roles",
                    match=MatchValue(value=user_role),
                )
            ]
        ),
        limit=limit,
    )
