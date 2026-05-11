#!/usr/bin/env python3
"""One-time migration: replace 'compliance' with 'admin' in Qdrant allowed_roles payloads."""
import argparse
import os
from qdrant_client import QdrantClient


def migrate(collection: str, url: str) -> None:
    client = QdrantClient(url=url)
    offset = None
    updated = 0
    while True:
        results, next_offset = client.scroll(
            collection_name=collection,
            with_payload=True,
            limit=100,
            offset=offset,
        )
        for point in results:
            roles = point.payload.get("allowed_roles", [])
            if "compliance" in roles:
                new_roles = ["admin" if r == "compliance" else r for r in roles]
                client.overwrite_payload(
                    collection_name=collection,
                    payload={"allowed_roles": new_roles},
                    points=[point.id],
                )
                updated += 1
        if next_offset is None:
            break
        offset = next_offset
    print(f"Updated {updated} points in '{collection}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "documents"))
    parser.add_argument("--url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    args = parser.parse_args()
    migrate(args.collection, args.url)
