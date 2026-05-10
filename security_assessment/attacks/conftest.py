import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.models.base import Base
from backend.main import app
from backend.core.database import get_db
from backend.core.security import create_access_token


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def adviser_token():
    """Token for a low-privilege adviser user."""
    return create_access_token({"sub": "adviser-001", "role": "adviser"})


@pytest_asyncio.fixture
def compliance_token():
    """Token for a compliance officer."""
    return create_access_token({"sub": "compliance-001", "role": "compliance"})
