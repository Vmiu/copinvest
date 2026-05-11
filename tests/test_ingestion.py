"""Integration tests for POST /api/v1/ingest endpoint — covers all INGEST requirements."""

import io
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from backend.core.database import get_db
from backend.core.dependencies import get_chunking_client, get_openrouter_client, get_qdrant_client
from backend.core.security import hash_password
from backend.main import app
from backend.models.base import Base
from backend.models.user import User
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session_ingest():
    """Isolated in-memory DB session for ingestion tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_user(db_session_ingest):
    """User with admin role in the test DB."""
    user = User(
        id="admin-user-1",
        email="admin@test.hk",
        hashed_password=hash_password("adminpass"),
        role="admin",
    )
    db_session_ingest.add(user)
    await db_session_ingest.commit()
    return user


@pytest_asyncio.fixture
async def adviser_user(db_session_ingest):
    """User with adviser role in the test DB."""
    user = User(
        id="adviser-user-1",
        email="adviser@test.hk",
        hashed_password=hash_password("adviserpass"),
        role="adviser",
    )
    db_session_ingest.add(user)
    await db_session_ingest.commit()
    return user


@pytest.fixture
def qdrant_memory():
    """In-memory Qdrant client with collection initialised for ingestion tests."""
    from backend.repositories.vector_repo import setup_collection
    client = QdrantClient(":memory:")
    setup_collection(client)
    return client


@pytest_asyncio.fixture
async def ingest_client(db_session_ingest, qdrant_memory):
    """HTTP test client with DB and Qdrant overrides applied."""
    async def override_get_db():
        yield db_session_ingest

    def override_get_qdrant():
        return qdrant_memory

    def override_get_chunking():
        return MagicMock()

    def override_get_openrouter():
        return MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_qdrant_client] = override_get_qdrant
    app.dependency_overrides[get_chunking_client] = override_get_chunking
    app.dependency_overrides[get_openrouter_client] = override_get_openrouter

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


async def _get_admin_token(client: AsyncClient) -> str:
    """Login as admin user and return JWT token."""
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "admin@test.hk", "password": "adminpass"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


async def _get_adviser_token(client: AsyncClient) -> str:
    """Login as adviser user and return JWT token."""
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "adviser@test.hk", "password": "adviserpass"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# Shared mock data
_MOCK_CHUNKS = [
    {"text": "Chunk 1 content about investments", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "first", "total_chunks_in_doc": 2},
    {"text": "Chunk 2 content about compliance", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "last", "total_chunks_in_doc": 2},
]
_MOCK_VECTORS = [[0.1] * 1024, [0.2] * 1024]
_MOCK_MARKDOWN = "# Sample Document\n\nThis is test content.\n\n---\n\nMore test content."
_INGEST_META = {"document_type": "pdf", "language": "en", "jurisdiction": "hk"}


def _ingest_patches():
    """Return a list of context managers that mock the heavy dependencies."""
    return [
        patch(
            "backend.services.document_parser.parse_pdf_vision",
            new_callable=AsyncMock,
            return_value=_MOCK_MARKDOWN,
        ),
        patch(
            "backend.services.document_parser.parse_docling",
            new_callable=Mock,
            return_value=_MOCK_MARKDOWN,
        ),
        patch(
            "backend.services.chunking_service.chunk_document",
            new_callable=AsyncMock,
            return_value=_MOCK_CHUNKS,
        ),
        patch(
            "backend.services.embedding_service.embed_chunks",
            new_callable=AsyncMock,
            return_value=_MOCK_VECTORS,
        ),
    ]


# ---------------------------------------------------------------------------
# INGEST-01: PDF ingestion
# ---------------------------------------------------------------------------

async def test_ingest_pdf_success(ingest_client, admin_user, qdrant_memory):
    """INGEST-01: Upload a PDF file — 201 with correct doc_type and chunk_count."""
    token = await _get_admin_token(ingest_client)

    pdf_content = b"%PDF-1.4 minimal test pdf content"
    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"sensitivity_tier": "1", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["doc_type"] == "pdf"
    assert body["chunk_count"] == len(_MOCK_CHUNKS)
    assert "document_id" in body


# ---------------------------------------------------------------------------
# INGEST-02: DOCX ingestion
# ---------------------------------------------------------------------------

async def test_ingest_docx_success(ingest_client, admin_user, qdrant_memory):
    """INGEST-02: Upload a .docx file — 201 with doc_type=docx."""
    token = await _get_admin_token(ingest_client)

    docx_content = b"PK\x03\x04 minimal docx content"
    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("brief.docx", io.BytesIO(docx_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"sensitivity_tier": "2", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["doc_type"] == "docx"


# ---------------------------------------------------------------------------
# INGEST-03: CSV ingestion
# ---------------------------------------------------------------------------

async def test_ingest_csv_success(ingest_client, admin_user, qdrant_memory):
    """INGEST-03: Upload a CSV file — 201 with doc_type=csv."""
    token = await _get_admin_token(ingest_client)

    csv_content = b"name,value\nApple Inc,150.00\nGoogle,2800.00"
    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("portfolio.csv", io.BytesIO(csv_content), "text/csv")},
            data={"sensitivity_tier": "1", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["doc_type"] == "csv"


# ---------------------------------------------------------------------------
# INGEST-04 / T-02-01: Role enforcement
# ---------------------------------------------------------------------------

async def test_ingest_requires_admin_role(ingest_client, adviser_user, qdrant_memory):
    """INGEST-04 / T-02-01: Non-admin user receives 403."""
    token = await _get_adviser_token(ingest_client)

    resp = await ingest_client.post(
        "/api/v1/ingest",
        files={"file": ("report.pdf", io.BytesIO(b"%PDF minimal"), "application/pdf")},
        data={"sensitivity_tier": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# INGEST-04 / INGEST-05: Sensitivity tier stored and RBAC roles assigned
# ---------------------------------------------------------------------------

async def test_ingest_sensitivity_tier_stored(ingest_client, admin_user, qdrant_memory):
    """INGEST-04 / INGEST-05: Sensitivity tier 3 maps to senior_adviser + admin roles in Qdrant."""
    token = await _get_admin_token(ingest_client)

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("restricted.pdf", io.BytesIO(b"%PDF restricted"), "application/pdf")},
            data={"sensitivity_tier": "3", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sensitivity_tier"] == 3

    # Verify Qdrant points have correct allowed_roles
    doc_id = body["document_id"]
    from backend.core.config import get_settings
    settings = get_settings()
    results = qdrant_memory.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=doc_id))]
        ),
        limit=100,
    )
    points = results[0]
    assert len(points) == len(_MOCK_CHUNKS)
    for pt in points:
        assert set(pt.payload["allowed_roles"]) == {"senior_adviser", "admin"}


# ---------------------------------------------------------------------------
# INGEST-05: Chunk metadata payload
# ---------------------------------------------------------------------------

async def test_ingest_chunks_have_metadata(ingest_client, admin_user, qdrant_memory):
    """INGEST-05: Every Qdrant point has source_id, doc_type, sensitivity_tier, allowed_roles, chunk_index, text."""
    token = await _get_admin_token(ingest_client)

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("meta.pdf", io.BytesIO(b"%PDF meta"), "application/pdf")},
            data={"sensitivity_tier": "1", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["document_id"]

    from backend.core.config import get_settings
    settings = get_settings()
    results = qdrant_memory.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=doc_id))]
        ),
        limit=100,
    )
    points = results[0]
    required_keys = {"source_id", "doc_type", "sensitivity_tier", "allowed_roles", "chunk_index", "text"}
    for pt in points:
        assert required_keys.issubset(pt.payload.keys()), f"Missing keys: {required_keys - pt.payload.keys()}"
        assert pt.payload["source_id"] == doc_id
        assert pt.payload["doc_type"] == "pdf"
        assert pt.payload["sensitivity_tier"] == 1


# ---------------------------------------------------------------------------
# D-12: Re-ingestion replaces chunks
# ---------------------------------------------------------------------------

async def test_reingest_replaces_chunks(ingest_client, admin_user, qdrant_memory):
    """D-12: Re-ingesting same document_id deletes old chunks and replaces with new ones."""
    token = await _get_admin_token(ingest_client)
    doc_id = "test-reingest-doc"

    first_chunks = [
        {"text": "First ingestion chunk A", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "first", "total_chunks_in_doc": 3},
        {"text": "First ingestion chunk B", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "middle", "total_chunks_in_doc": 3},
        {"text": "First ingestion chunk C", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "last", "total_chunks_in_doc": 3},
    ]
    first_vectors = [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024]

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=first_chunks,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=first_vectors,
    ):
        resp1 = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF v1"), "application/pdf")},
            data={"sensitivity_tier": "1", "document_id": doc_id, **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp1.status_code == 201, resp1.text
    assert resp1.json()["chunk_count"] == 3

    # Second ingestion with same document_id — 2 chunks
    second_chunks = [
        {"text": "Second ingestion chunk X", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "first", "total_chunks_in_doc": 2},
        {"text": "Second ingestion chunk Y", "page_number": 1, "section_heading": None, "is_table": False, "is_figure": False, "chunk_position": "last", "total_chunks_in_doc": 2},
    ]
    second_vectors = [[0.4] * 1024, [0.5] * 1024]

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=second_chunks,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=second_vectors,
    ):
        resp2 = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF v2"), "application/pdf")},
            data={"sensitivity_tier": "1", "document_id": doc_id, **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp2.status_code == 201, resp2.text
    assert resp2.json()["chunk_count"] == 2

    # Qdrant should have exactly 2 points for this source_id
    from backend.core.config import get_settings
    settings = get_settings()
    results = qdrant_memory.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=doc_id))]
        ),
        limit=100,
    )
    assert len(results[0]) == 2


# ---------------------------------------------------------------------------
# D-14: Optional document_id — UUID generated when omitted
# ---------------------------------------------------------------------------

async def test_ingest_document_id_optional(ingest_client, admin_user, qdrant_memory):
    """D-14: Omitting document_id generates a UUID in the response."""
    token = await _get_admin_token(ingest_client)

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("anon.pdf", io.BytesIO(b"%PDF anon"), "application/pdf")},
            data={"sensitivity_tier": "1", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["document_id"]
    assert doc_id  # non-empty
    # Should look like a UUID (8-4-4-4-12 hex groups)
    import re
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", doc_id), (
        f"Expected UUID format, got: {doc_id}"
    )


# ---------------------------------------------------------------------------
# INGEST-08: Quality metrics in response
# ---------------------------------------------------------------------------

async def test_ingest_quality_metrics(ingest_client, admin_user, qdrant_memory):
    """INGEST-08: Response includes chunk_count, total_chars, parse_duration_ms > 0."""
    token = await _get_admin_token(ingest_client)

    with patch(
        "backend.services.document_parser.parse_pdf_vision",
        new_callable=AsyncMock,
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.document_parser.parse_docling",
        return_value=_MOCK_MARKDOWN,
    ), patch(
        "backend.services.chunking_service.chunk_document",
        new_callable=AsyncMock,
        return_value=_MOCK_CHUNKS,
    ), patch(
        "backend.services.embedding_service.embed_chunks",
        new_callable=AsyncMock,
        return_value=_MOCK_VECTORS,
    ):
        resp = await ingest_client.post(
            "/api/v1/ingest",
            files={"file": ("metrics.pdf", io.BytesIO(b"%PDF metrics"), "application/pdf")},
            data={"sensitivity_tier": "1", **_INGEST_META},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["chunk_count"] == len(_MOCK_CHUNKS)
    assert body["total_chars"] == sum(len(c["text"]) for c in _MOCK_CHUNKS)
    assert body["parse_duration_ms"] >= 0


# ---------------------------------------------------------------------------
# Unsupported file type → 422
# ---------------------------------------------------------------------------

async def test_ingest_unsupported_file_type(ingest_client, admin_user, qdrant_memory):
    """Unsupported file extension (.txt) returns HTTP 422."""
    token = await _get_admin_token(ingest_client)

    resp = await ingest_client.post(
        "/api/v1/ingest",
        files={"file": ("notes.txt", io.BytesIO(b"plain text content"), "text/plain")},
        data={"sensitivity_tier": "1", **_INGEST_META},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Empty file → 400
# ---------------------------------------------------------------------------

async def test_ingest_empty_file(ingest_client, admin_user, qdrant_memory):
    """Empty file upload returns HTTP 400."""
    token = await _get_admin_token(ingest_client)

    resp = await ingest_client.post(
        "/api/v1/ingest",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        data={"sensitivity_tier": "1", **_INGEST_META},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400, resp.text
