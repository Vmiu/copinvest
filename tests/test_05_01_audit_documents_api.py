"""Integration tests for GET /api/v1/audit and GET /api/v1/documents endpoints."""

from datetime import datetime, timezone

import pytest_asyncio

from backend.core.security import create_access_token, hash_password
from backend.models.audit_log import AuditLog, Session as AuditSession
from backend.models.document import DocumentRecord
from backend.models.enums import AuditStatus
from backend.models.user import User


def _compliance_token(user_id: str = "compliance-user") -> str:
    return create_access_token({"sub": user_id, "role": "compliance"})


def _adviser_token(user_id: str = "adviser-user") -> str:
    return create_access_token({"sub": user_id, "role": "adviser"})


@pytest_asyncio.fixture
async def seeded_compliance_user(db_session):
    user = User(
        id="compliance-user",
        email="compliance@test.hk",
        hashed_password=hash_password("pw"),
        role="compliance",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def seeded_audit_data(db_session, seeded_compliance_user):
    session = AuditSession(
        id="sess-1",
        user_id="compliance-user",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    logs = [
        AuditLog(
            id=f"trace-{i}",
            session_id="sess-1",
            user_id="compliance-user",
            timestamp=datetime.now(timezone.utc),
            channel="web",
            query_text=f"query {i}",
            status=AuditStatus.completed,
        )
        for i in range(3)
    ]
    for log in logs:
        db_session.add(log)
    await db_session.flush()
    return logs


@pytest_asyncio.fixture
async def seeded_document_data(db_session, seeded_compliance_user):
    docs = [
        DocumentRecord(
            document_id=f"doc-{i}",
            filename=f"file{i}.pdf",
            doc_type="pdf",
            sensitivity_tier=1,
            chunk_count=10,
            total_chars=1000,
            parse_duration_ms=200,
            extraction_method="docling",
            ingested_by="compliance-user",
        )
        for i in range(2)
    ]
    for doc in docs:
        db_session.add(doc)
    await db_session.flush()
    return docs


# --- Audit list endpoint ---

async def test_audit_list_requires_auth(client):
    resp = await client.get("/api/v1/audit")
    assert resp.status_code in (401, 403)


async def test_audit_list_requires_compliance_role(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {_adviser_token()}"},
    )
    assert resp.status_code == 403


async def test_audit_list_returns_items(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["page"] == 1
    assert body["limit"] == 25


async def test_audit_list_pagination(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit?page=1&limit=2",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2


async def test_audit_list_filter_by_user(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit?user_id=compliance-user",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3


async def test_audit_list_filter_by_session(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit?session_id=sess-1",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3


async def test_audit_list_filter_no_match(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit?user_id=nobody",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# --- Audit detail endpoint ---

async def test_audit_detail_returns_record(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit/trace-0",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "trace-0"
    assert body["query_text"] == "query 0"
    assert body["channel"] == "web"


async def test_audit_detail_not_found(client, seeded_compliance_user):
    resp = await client.get(
        "/api/v1/audit/nonexistent",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 404


async def test_audit_detail_requires_compliance_role(client, seeded_audit_data):
    resp = await client.get(
        "/api/v1/audit/trace-0",
        headers={"Authorization": f"Bearer {_adviser_token()}"},
    )
    assert resp.status_code == 403


# --- Documents list endpoint ---

async def test_documents_list_requires_auth(client):
    resp = await client.get("/api/v1/documents")
    assert resp.status_code in (401, 403)


async def test_documents_list_requires_compliance_role(client, seeded_document_data):
    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_adviser_token()}"},
    )
    assert resp.status_code == 403


async def test_documents_list_returns_items(client, seeded_document_data):
    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_documents_list_item_fields(client, seeded_document_data):
    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "document_id" in item
    assert "filename" in item
    assert "sensitivity_tier" in item
    assert "chunk_count" in item
    assert "ingested_at" in item
    assert "ingested_by" in item


async def test_documents_list_empty(client, seeded_compliance_user):
    resp = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {_compliance_token()}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
