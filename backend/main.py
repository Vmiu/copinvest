from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from backend.core.database import engine
from backend.models.base import Base
from backend.repositories.vector_repo import get_qdrant_client, setup_collection
from backend.routers.auth import router as auth_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        qdrant = get_qdrant_client()
        setup_collection(qdrant)
    except Exception:
        logger.warning(
            "qdrant_init_failed",
            msg="Qdrant not available at startup — collection setup skipped",
        )

    yield
    await engine.dispose()


app = FastAPI(title="CopInvest", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
