"""
Batch-ingest all MPF PDF documents into Qdrant.

Usage:
    uv run python -m backend.scripts.ingest_all_pdfs

Requires:
    - Ollama running with nomic-embed-text model pulled
    - Qdrant running (Docker) OR falls back to in-memory
"""
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import fitz  # PyMuPDF
import httpx
import structlog

from backend.core.config import get_settings
from backend.repositories.vector_repo import get_qdrant_client, setup_collection, upsert_chunks

logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).parents[2]

# Document folders → (sensitivity_tier, allowed_roles)
FOLDER_CONFIG: dict[str, tuple[int, list[str]]] = {
    "宏利信託契據":         (3, ["senior_adviser", "compliance"]),
    "宏利強積金基金概覽":   (1, ["adviser", "senior_adviser", "compliance"]),
    "宏利強積金計劃說明書": (2, ["senior_adviser", "compliance"]),
    "宏利綜合月結報告":     (4, ["compliance"]),
    "滙豐信託契據":         (3, ["senior_adviser", "compliance"]),
    "滙豐強積金基金概覽":   (1, ["adviser", "senior_adviser", "compliance"]),
    "滙豐強積金基金表現一覽": (1, ["adviser", "senior_adviser", "compliance"]),
    "滙豐強積金每月基金表現摘要": (1, ["adviser", "senior_adviser", "compliance"]),
    "滙豐強積金聲明":       (2, ["senior_adviser", "compliance"]),
    "滙豐強積金計劃說明書": (3, ["senior_adviser", "compliance"]),
    "費用及收費":           (2, ["senior_adviser", "compliance"]),
}

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def simple_chunk(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count, respecting paragraph boundaries."""
    if not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of current chunk
            current = current[-overlap:] + "\n\n" + para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 20]


async def embed_batch(chunks: list[str], model: str) -> list[list[float]]:
    """Embed chunks via Ollama API, batching to avoid payload limits."""
    BATCH_SIZE = 20
    all_vectors = []
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            # Truncate any excessively long chunks
            batch = [c[:4000] for c in batch]
            resp = await client.post(
                OLLAMA_EMBED_URL,
                json={"model": model, "input": batch},
            )
            if resp.status_code != 200:
                # Fall back to one-by-one for this batch
                for chunk in batch:
                    r = await client.post(
                        OLLAMA_EMBED_URL,
                        json={"model": model, "input": chunk[:2000]},
                    )
                    r.raise_for_status()
                    all_vectors.append(r.json()["embeddings"][0])
            else:
                all_vectors.extend(resp.json()["embeddings"])
    return all_vectors


async def ingest_folder(
    folder_name: str,
    tier: int,
    allowed_roles: list[str],
    qdrant_client,
    settings,
) -> list[dict]:
    """Ingest all PDFs in a folder."""
    folder_path = PROJECT_ROOT / folder_name
    if not folder_path.exists():
        logger.warning("folder_missing", folder=folder_name)
        return []

    pdfs = sorted(folder_path.glob("*.pdf"))
    if not pdfs:
        logger.warning("no_pdfs", folder=folder_name)
        return []

    results = []
    for pdf_path in pdfs:
        start = time.monotonic()
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            logger.warning("empty_pdf", file=pdf_path.name)
            continue

        chunks = simple_chunk(text)
        if not chunks:
            continue

        vectors = await embed_batch(chunks, settings.embedding_model)

        source_id = f"{folder_name}/{pdf_path.name}"
        payload_base = {
            "source_id": source_id,
            "folder": folder_name,
            "filename": pdf_path.name,
            "sensitivity_tier": tier,
            "allowed_roles": allowed_roles,
        }

        count, _ = upsert_chunks(qdrant_client, chunks, vectors, payload_base)
        elapsed = int((time.monotonic() - start) * 1000)

        results.append({
            "source": source_id,
            "chunks": count,
            "tier": tier,
            "duration_ms": elapsed,
        })
        logger.info("ingested", source=source_id, chunks=count, tier=tier, ms=elapsed)

    return results


async def main():
    settings = get_settings()
    qdrant = get_qdrant_client()
    setup_collection(qdrant)

    print("\n" + "=" * 60)
    print("  CopInvest — Batch PDF Ingestion")
    print("=" * 60)
    print(f"  Embedding model: {settings.embedding_model}")
    print(f"  Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"  Collection: {settings.qdrant_collection}")
    print("=" * 60 + "\n")

    all_results = []
    for folder_name, (tier, roles) in FOLDER_CONFIG.items():
        results = await ingest_folder(folder_name, tier, roles, qdrant, settings)
        all_results.extend(results)

    print("\n" + "=" * 60)
    print("  Ingestion Summary")
    print("=" * 60)
    total_chunks = 0
    for r in all_results:
        print(f"  [{r['tier']}] {r['source']}: {r['chunks']} chunks ({r['duration_ms']}ms)")
        total_chunks += r["chunks"]
    print(f"\n  Total documents: {len(all_results)}")
    print(f"  Total chunks: {total_chunks}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
