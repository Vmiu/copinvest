"""Integration tests for auth router — login endpoint and protected access."""

import jwt
import pytest_asyncio

from backend.core.security import hash_password
from backend.models.user import User


@pytest_asyncio.fixture
async def seeded_user(db_session):
    """Create a test user with known credentials in the test DB."""
    user = User(
        id="test-user-1",
        email="alice@test.hk",
        hashed_password=hash_password("password123"),
        role="adviser",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def test_login_success(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "alice@test.hk", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_bad_password(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "alice@test.hk", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "nobody@test.hk", "password": "password123"},
    )
    assert response.status_code == 401


async def test_token_contains_role(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "alice@test.hk", "password": "password123"},
    )
    token = response.json()["access_token"]
    # Decode without verification to inspect claims
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["role"] == "adviser"


async def test_protected_endpoint_no_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


async def test_protected_endpoint_valid_token(client, seeded_user):
    # Login first
    login_resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "alice@test.hk", "password": "password123"},
    )
    token = login_resp.json()["access_token"]
    # Access protected endpoint
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "test-user-1"
    assert body["role"] == "adviser"
