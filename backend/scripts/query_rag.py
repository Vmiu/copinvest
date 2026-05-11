"""
Interactive local RAG query CLI.

Usage:
    uv run python -m backend.scripts.query_rag
    uv run python -m backend.scripts.query_rag --role adviser
    uv run python -m backend.scripts.query_rag --role compliance --query "滙豐強積金費用"

Requires:
    - Ollama running with nomic-embed-text + qwen2.5-coder:7b
    - Qdrant with ingested documents (run ingest_all_pdfs.py first)
"""
import argparse
import asyncio

import httpx
from openai import AsyncOpenAI

from backend.core.config import get_settings
from backend.repositories.vector_repo import get_qdrant_client, query_with_rbac
from backend.services.generation_service import generate_answer

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"


async def embed_query(text: str, model: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": model, "input": text},
        )
        resp.raise_for_status()
    return resp.json()["embeddings"][0]


async def run_query(query: str, role: str, top_k: int = 5):
    settings = get_settings()
    qdrant = get_qdrant_client()

    # Embed query
    query_vector = await embed_query(query, settings.embedding_model)

    # Retrieve with RBAC
    results = query_with_rbac(qdrant, query_vector, role, limit=top_k)
    chunks = results.points

    if not chunks:
        print("\n  [!] No relevant chunks found for your role.\n")
        return

    # Print retrieved chunks
    print(f"\n{'─' * 60}")
    print(f"  Retrieved {len(chunks)} chunks (role={role})")
    print(f"{'─' * 60}")
    for i, pt in enumerate(chunks, 1):
        source = pt.payload.get("source_id", "?")
        tier = pt.payload.get("sensitivity_tier", "?")
        text = pt.payload.get("text", "")[:200]
        print(f"\n  [{i}] {source} (tier={tier}, score={pt.score:.3f})")
        print(f"      {text}...")

    # Generate answer
    print(f"\n{'─' * 60}")
    print("  Generating answer...")
    print(f"{'─' * 60}")

    client = AsyncOpenAI(base_url=settings.ollama_base_url, api_key="ollama")
    result = await generate_answer(query, chunks, client)

    print(f"\n  Answer:\n  {result['answer']}")
    if result["sources"]:
        print(f"\n  Sources: {result['sources']}")
    print(f"  Model: {result['model_used']}")
    print(f"  Tokens: {result['prompt_tokens']}+{result['completion_tokens']}")
    print()


async def interactive(role: str):
    print(f"\n  CopInvest RAG Query (role={role})")
    print("  Type 'quit' to exit, 'role <name>' to switch role\n")

    current_role = role
    while True:
        try:
            query = input(f"  [{current_role}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue
        if query.lower() == "quit":
            break
        if query.lower().startswith("role "):
            current_role = query.split(" ", 1)[1].strip()
            print(f"  Switched to role: {current_role}")
            continue

        await run_query(query, current_role)


def main():
    parser = argparse.ArgumentParser(description="CopInvest local RAG query")
    parser.add_argument("--role", default="adviser", choices=["adviser", "senior_adviser", "compliance"])
    parser.add_argument("--query", "-q", help="Single query (non-interactive)")
    args = parser.parse_args()

    if args.query:
        asyncio.run(run_query(args.query, args.role))
    else:
        asyncio.run(interactive(args.role))


if __name__ == "__main__":
    main()
