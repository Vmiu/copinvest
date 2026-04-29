from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.core.database import engine
from backend.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="CopInvest", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
