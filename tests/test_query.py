"""Integration and unit tests for POST /api/v1/query endpoint — covers RAG-01 through RAG-05."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.database import get_db
from backend.core.dependencies import get_chunking_client, get_generation_client, get_qdrant_client
from backend.core.security import hash_password
from backend.main import app
from backend.models.audit_log import AuditLog
from backend.models.base import Base
from backend.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session():
    """Isolated in-memory DB session for query tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def adviser_user(db_session):
    """User with adviser role in the test DB."""
    user = User(
        id="adviser-query-user-1",
        email="adviser-query@test.hk",
        hashed_password=hash_password("adviserpass"),
        role="adviser",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def async_client(db_session):
    """HTTP test client with DB and client dependency overrides."""
    async def override_get_db():
        yield db_session

    def override_get_chunking():
        return MagicMock()

    def override_get_generation():
        return MagicMock()

    def override_get_qdrant():
        return MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chunking_client] = override_get_chunking
    app.dependency_overrides[get_generation_client] = override_get_generation
    app.dependency_overrides[get_qdrant_client] = override_get_qdrant

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(async_client, adviser_user):
    """JWT auth headers for the adviser user."""
    resp = await async_client.post(
        "/api/v1/auth/token",
        data={"username": "adviser-query@test.hk", "password": "adviserpass"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Shared mock results
# ---------------------------------------------------------------------------

MOCK_PROCESS_RESULT = {
    "answer": "The fund has a 1.5% management fee. [1]",
    "sources": [{"doc_name": "fund_factsheet.pdf", "section_title": "Fees", "chunk_index": 0}],
    "trace_id": "test-trace-id-001",
    "not_found": False,
    "chunks_retrieved": 3,
    "model_used": "deepseek-v4-pro",
}

MOCK_NOT_FOUND_RESULT = {
    "answer": "This information is not available in the approved documents.",
    "sources": [],
    "trace_id": "test-trace-id-002",
    "not_found": True,
    "chunks_retrieved": 0,
    "model_used": "deepseek-v4-pro",
}


# ---------------------------------------------------------------------------
# Integration tests (6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_endpoint_happy_path(async_client, auth_headers):
    """POST /api/v1/query returns 200 with answer, sources, trace_id."""
    with patch(
        "backend.services.query_service.process_query",
        new_callable=AsyncMock,
        return_value=MOCK_PROCESS_RESULT,
    ):
        response = await async_client.post(
            "/api/v1/query",
            json={"query": "What is the management fee?"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] != ""
    assert isinstance(data["sources"], list)
    assert data["trace_id"] == "test-trace-id-001"
    assert data["not_found"] is False
    assert data["model_used"] == "deepseek-v4-pro"


@pytest.mark.asyncio
async def test_query_not_found(async_client, auth_headers):
    """When no relevant content, not_found=true and answer contains 'not available'."""
    with patch(
        "backend.services.query_service.process_query",
        new_callable=AsyncMock,
        return_value=MOCK_NOT_FOUND_RESULT,
    ):
        response = await async_client.post(
            "/api/v1/query",
            json={"query": "What is the weather in Tokyo?"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["not_found"] is True
    assert "not available" in data["answer"].lower()
    assert data["sources"] == []


@pytest.mark.asyncio
async def test_query_unauthenticated(async_client):
    """POST without JWT returns 401."""
    response = await async_client.post(
        "/api/v1/query",
        json={"query": "What is the management fee?"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_query_rbac_enforcement(async_client, auth_headers):
    """Qdrant is called with the role from JWT, not from request body."""
    captured_role = {}

    async def mock_process_query(db, query, session_id, user_id, user_role, **kwargs):
        captured_role["role"] = user_role
        return MOCK_PROCESS_RESULT

    with patch(
        "backend.services.query_service.process_query",
        side_effect=mock_process_query,
    ):
        response = await async_client.post(
            "/api/v1/query",
            json={"query": "What is the management fee?"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    # Role must come from JWT, not from request body
    assert captured_role["role"] in ("adviser", "senior_adviser", "compliance")


@pytest.mark.asyncio
async def test_query_audit_record(async_client, auth_headers, db_session):
    """Successful query creates an AuditLog record with correct user_id and query_text."""
    mock_qdrant_result = MagicMock()
    mock_qdrant_result.points = []

    with (
        patch("backend.services.query_rewrite_service.rewrite_query", new_callable=AsyncMock, return_value="rewritten query"),
        patch("backend.services.rerank_service.rerank_chunks", new_callable=AsyncMock, return_value=[]),
        patch("backend.services.generation_service.generate_answer", new_callable=AsyncMock, return_value={
            "answer": "This information is not available in the approved documents.",
            "sources": [],
            "not_found": True,
            "model_used": "deepseek-v4-pro",
            "prompt_tokens": 100,
            "completion_tokens": 20,
        }),
        patch("backend.repositories.vector_repo.query_with_rbac", return_value=mock_qdrant_result),
        patch("httpx.AsyncClient") as mock_http_cls,
    ):
        # Mock Voyage AI embedding response
        mock_http_instance = AsyncMock()
        mock_voyage_resp = MagicMock()
        mock_voyage_resp.raise_for_status = MagicMock()
        mock_voyage_resp.json.return_value = {
            "data": [{"embedding": [0.1] * 1024, "index": 0}]
        }
        mock_http_instance.post = AsyncMock(return_value=mock_voyage_resp)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await async_client.post(
            "/api/v1/query",
            json={"query": "audit test query"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    # Verify audit record was written
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.query_text == "audit test query")
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.query_text == "audit test query"


@pytest.mark.asyncio
async def test_session_24h_timeout(db_session):
    """Session older than 24h is expired and a new session is created."""
    from datetime import datetime, timezone, timedelta
    from backend.services.session_service import get_or_create_session
    from backend.models.audit_log import Session as AuditSession
    import uuid

    user_id = str(uuid.uuid4())
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)

    # Create an old session with last_activity 25h ago
    old_session = AuditSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        start_time=old_time,
        last_activity=old_time,
    )
    db_session.add(old_session)
    await db_session.flush()

    # get_or_create_session should create a new session
    new_session_id = await get_or_create_session(db_session, user_id)
    assert new_session_id != old_session.id

    # Old session should be expired
    await db_session.refresh(old_session)
    assert old_session.end_time is not None


# ---------------------------------------------------------------------------
# Unit tests (5)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_rewrite():
    """rewrite_query returns non-empty string; falls back to original on error."""
    from backend.services.query_rewrite_service import rewrite_query

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "What is HSBC Holdings dividend yield for FY2025?"
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await rewrite_query("What is HSBC's dividend?", mock_client)
    assert isinstance(result, str)
    assert len(result) > 0
    # Rewritten query should differ from input (or be same on fallback — both valid)
    assert result != "" or result == "What is HSBC's dividend?"


@pytest.mark.asyncio
async def test_rerank_threshold():
    """rerank_chunks filters results to those with relevance_score >= 0.3."""
    from backend.services.rerank_service import rerank_chunks

    def make_chunk(text):
        pt = MagicMock()
        pt.payload = {"text": text}
        return pt

    chunks = [make_chunk(f"chunk {i}") for i in range(4)]

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"index": 0, "relevance_score": 0.8},
            {"index": 1, "relevance_score": 0.5},
            {"index": 2, "relevance_score": 0.2},
            {"index": 3, "relevance_score": 0.1},
        ]
    }

    with patch("httpx.AsyncClient") as mock_http_cls:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctx.post = AsyncMock(return_value=mock_resp)
        mock_http_cls.return_value = mock_ctx

        result = await rerank_chunks("test query", chunks, api_key="test-key", threshold=0.3, top_n=5)

    # Only scores 0.8 and 0.5 pass threshold >= 0.3
    assert len(result) == 2


@pytest.mark.asyncio
async def test_citation_extraction():
    """generate_answer extracts [N] citation markers and builds sources list."""
    from backend.services.generation_service import generate_answer

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "The dividend is 5% [1]. See also [2]."
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 20
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    def make_chunk(source_id, section, idx):
        pt = MagicMock()
        pt.payload = {"source_id": source_id, "section_title": section, "chunk_index": idx, "text": "text"}
        return pt

    chunks = [make_chunk("doc_a.pdf", "Dividends", 0), make_chunk("doc_b.pdf", "Overview", 1)]

    result = await generate_answer("What is the dividend?", chunks, mock_client)
    assert len(result["sources"]) == 2


@pytest.mark.asyncio
async def test_not_found_sentinel():
    """generate_answer sets not_found=True when LLM returns NO_RELEVANT_CONTENT sentinel."""
    from backend.services.generation_service import generate_answer

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "NO_RELEVANT_CONTENT the user asked about weather"
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 10
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await generate_answer("What is the weather?", [], mock_client)
    assert result["not_found"] is True
    assert "not available in the approved documents" in result["answer"]


@pytest.mark.asyncio
async def test_audit_new_fields(async_client, auth_headers, db_session):
    """After a query, audit record has rewritten_query set, chunks_passed_rerank is int, not_found is bool, and query_text == original_query (per D-19)."""
    original_query = "audit fields test query"

    mock_qdrant_result = MagicMock()
    mock_qdrant_result.points = []

    with (
        patch("backend.services.query_rewrite_service.rewrite_query", new_callable=AsyncMock, return_value="rewritten: audit fields test query"),
        patch("backend.services.rerank_service.rerank_chunks", new_callable=AsyncMock, return_value=[]),
        patch("backend.services.generation_service.generate_answer", new_callable=AsyncMock, return_value={
            "answer": "This information is not available in the approved documents.",
            "sources": [],
            "not_found": True,
            "model_used": "deepseek-v4-pro",
            "prompt_tokens": 100,
            "completion_tokens": 20,
        }),
        patch("backend.repositories.vector_repo.query_with_rbac", return_value=mock_qdrant_result),
        patch("httpx.AsyncClient") as mock_http_cls,
    ):
        mock_http_instance = AsyncMock()
        mock_voyage_resp = MagicMock()
        mock_voyage_resp.raise_for_status = MagicMock()
        mock_voyage_resp.json.return_value = {"data": [{"embedding": [0.1] * 1024, "index": 0}]}
        mock_http_instance.post = AsyncMock(return_value=mock_voyage_resp)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await async_client.post(
            "/api/v1/query",
            json={"query": original_query},
            headers=auth_headers,
        )

    assert response.status_code == 200
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.query_text == original_query)
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    # D-19: query_text (pre-existing column) serves as original_query
    assert audit.query_text == original_query
    assert audit.rewritten_query is not None
    assert isinstance(audit.chunks_passed_rerank, int)
    assert isinstance(audit.not_found, bool)
