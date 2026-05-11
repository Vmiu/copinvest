import asyncio
import json
from pathlib import Path

from backend.core.database import async_session, engine
from backend.models.base import Base
from backend.models.user import User


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    seed_path = Path(__file__).parent.parent / "seed_users.json"
    with open(seed_path) as f:
        users = json.load(f)

    async with async_session() as db:
        for u in users:
            db.add(
                User(
                    id=u["id"],
                    email=u["email"],
                    hashed_password=u["hashed_password"],
                    role=u["role"],
                )
            )
        await db.commit()
    print(f"Seeded {len(users)} users")


if __name__ == "__main__":
    asyncio.run(seed())
