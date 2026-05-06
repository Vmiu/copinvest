import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
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
            vectors_config=VectorParams(size=4096, distance=Distance.COSINE),
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
    client.create_payload_index(
        collection_name=name,
        field_name="source_id",
        field_schema=PayloadSchemaType.KEYWORD,
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


def upsert_chunks(
    client: QdrantClient,
    chunks: list[str],
    vectors: list[list[float]],
    payload_base: dict,
    collection: str | None = None,
) -> tuple[int, list[str]]:
    """Upsert chunks and return (count, list_of_point_ids)."""
    settings = get_settings()
    name = collection or settings.qdrant_collection
    point_ids = [str(uuid.uuid4()) for _ in chunks]
    points = [
        PointStruct(
            id=point_id,
            vector=vector,
            payload={**payload_base, "chunk_index": i, "text": chunk},
        )
        for i, (point_id, chunk, vector) in enumerate(zip(point_ids, chunks, vectors))
    ]
    client.upsert(collection_name=name, points=points)
    return len(points), point_ids


def delete_by_source(
    client: QdrantClient,
    source_id: str,
    collection: str | None = None,
) -> None:
    settings = get_settings()
    name = collection or settings.qdrant_collection
    client.delete(
        collection_name=name,
        points_selector=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]
        ),
    )


def delete_by_source_except_new(
    client: QdrantClient,
    source_id: str,
    new_point_ids: list[str],
    collection: str | None = None,
) -> None:
    """Delete all points for source_id that are NOT in new_point_ids.

    Used for write-then-replace atomicity: upsert new chunks first, then
    remove old chunks so there is no gap where the document has zero chunks.
    """
    from qdrant_client.models import HasIdCondition, IsEmptyCondition  # noqa: F401
    settings = get_settings()
    name = collection or settings.qdrant_collection
    # Scroll to find old point IDs for this source
    results, _ = client.scroll(
        collection_name=name,
        scroll_filter=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]
        ),
        limit=10_000,
        with_payload=False,
        with_vectors=False,
    )
    old_ids = [str(pt.id) for pt in results if str(pt.id) not in new_point_ids]
    if old_ids:
        from qdrant_client.models import PointIdsList
        client.delete(
            collection_name=name,
            points_selector=PointIdsList(points=old_ids),
        )
