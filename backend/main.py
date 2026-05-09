from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from backend.core.config import get_settings
from backend.core.database import engine
from backend.core.dependencies import init_clients
from backend.models.base import Base
from backend.repositories.vector_repo import get_qdrant_client, setup_collection
from backend.routers.audit import router as audit_router
from backend.routers.auth import router as auth_router
from backend.routers.documents import router as documents_router
from backend.routers.ingest import router as ingest_router
from backend.routers.query import router as query_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev-only: create tables directly. In production, use: uv run alembic upgrade head
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    chunking_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )
    generation_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )
    openrouter_client = AsyncOpenAI(
        api_key=settings.openroute_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    qdrant_client = get_qdrant_client()
    init_clients(chunking_client, openrouter_client, qdrant_client, generation_client)

    try:
        setup_collection(qdrant_client)
    except Exception as exc:
        logger.warning(
            "qdrant_init_failed",
            msg="Qdrant not available at startup — collection setup skipped",
            error=str(exc),
            error_type=type(exc).__name__,
        )

    yield
    await engine.dispose()


app = FastAPI(title="CopInvest", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(audit_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
