import uuid
from pathlib import Path

import structlog
from openai import OpenAI
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.core.config import get_settings

logger = structlog.get_logger()

CHUNK_SIZE = 500      # characters
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "text-embedding-3-small"

# Which roles can access each tier
TIER_ROLES: dict[str, list[str]] = {
    "internal": ["adviser", "senior_adviser", "compliance"],
    "restricted": ["senior_adviser", "compliance"],
}


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]  # drop tiny chunks


def _embed(texts: list[str], client: OpenAI) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def ingest_document(
    pdf_path: Path,
    sensitivity_tier: str,
    qdrant: QdrantClient,
    openai_client: OpenAI,
    collection: str | None = None,
) -> dict:
    settings = get_settings()
    collection = collection or settings.qdrant_collection
    allowed_roles = TIER_ROLES[sensitivity_tier]
    tier_int = 2 if sensitivity_tier == "internal" else 3  # maps to SensitivityTier enum

    logger.info("ingesting_document", path=str(pdf_path), tier=sensitivity_tier)

    text = _extract_text(pdf_path)
    chunks = _chunk_text(text)

    logger.info("chunks_created", count=len(chunks), source=pdf_path.name)

    # Embed in batches of 100
    all_embeddings = []
    for i in range(0, len(chunks), 100):
        batch = chunks[i : i + 100]
        all_embeddings.extend(_embed(batch, openai_client))

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "source": pdf_path.name,
                "sensitivity_tier": tier_int,
                "allowed_roles": allowed_roles,
                "chunk_index": idx,
                "text": chunk,
            },
        )
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings))
    ]

    qdrant.upsert(collection_name=collection, points=points)

    logger.info("ingestion_complete", source=pdf_path.name, points=len(points))
    return {"source": pdf_path.name, "chunks": len(points), "tier": sensitivity_tier}
