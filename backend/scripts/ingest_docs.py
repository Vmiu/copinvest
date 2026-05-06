"""
Run from project root:
    python -m backend.scripts.ingest_docs
"""
import os
from pathlib import Path

from openai import OpenAI

from backend.repositories.vector_repo import get_qdrant_client, setup_collection
from backend.services.ingestion_service import ingest_document

DOCS_ROOT = Path(__file__).parents[3] / "docs"


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    openai_client = OpenAI(api_key=api_key)
    qdrant = get_qdrant_client()
    setup_collection(qdrant)

    results = []
    for tier in ("internal", "restricted"):
        tier_dir = DOCS_ROOT / tier
        if not tier_dir.exists():
            continue
        for pdf in sorted(tier_dir.glob("*.pdf")):
            result = ingest_document(pdf, tier, qdrant, openai_client)
            results.append(result)

    print("\n=== Ingestion Summary ===")
    for r in results:
        print(f"  {r['source']}: {r['chunks']} chunks ({r['tier']})")
    print(f"\nTotal documents: {len(results)}")


if __name__ == "__main__":
    main()
