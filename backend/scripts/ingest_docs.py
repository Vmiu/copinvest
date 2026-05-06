"""
Run from project root:
    python -m backend.scripts.ingest_docs
"""
from pathlib import Path

from ollama import Client as OllamaClient

from backend.core.config import get_settings
from backend.repositories.vector_repo import get_qdrant_client, setup_collection
from backend.services.ingestion_service import ingest_document

DOCS_ROOT = Path(__file__).parents[3] / "docs"


def main():
    settings = get_settings()
    ollama_client = OllamaClient(host=settings.ollama_base_url)
    qdrant = get_qdrant_client()
    setup_collection(qdrant)

    results = []
    for tier in ("internal", "restricted"):
        tier_dir = DOCS_ROOT / tier
        if not tier_dir.exists():
            continue
        for pdf in sorted(tier_dir.glob("*.pdf")):
            result = ingest_document(pdf, tier, qdrant, ollama_client)
            results.append(result)

    print("\n=== Ingestion Summary ===")
    for r in results:
        print(f"  {r['source']}: {r['chunks']} chunks ({r['tier']})")
    print(f"\nTotal documents: {len(results)}")


if __name__ == "__main__":
    main()
