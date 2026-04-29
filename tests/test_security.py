"""Tests for backend.core.security — JWT and password hashing utilities."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest


def test_hash_password():
    from backend.core.security import hash_password

    hashed = hash_password("test123")
    assert isinstance(hashed, str)
    assert hashed != "test123"


def test_verify_password_correct():
    from backend.core.security import hash_password, verify_password

    hashed = hash_password("test123")
    assert verify_password("test123", hashed) is True


def test_verify_password_wrong():
    from backend.core.security import hash_password, verify_password

    hashed = hash_password("test123")
    assert verify_password("wrong", hashed) is False


def test_create_access_token():
    from backend.core.security import create_access_token

    token = create_access_token({"sub": "user1", "role": "adviser"})
    assert isinstance(token, str)
    # JWT has 3 dot-separated parts
    assert len(token.split(".")) == 3


def test_jwt_contains_role():
    from backend.core.security import create_access_token, decode_access_token

    token = create_access_token({"sub": "user1", "role": "adviser"})
    payload = decode_access_token(token)
    assert payload["role"] == "adviser"


def test_jwt_contains_sub():
    from backend.core.security import create_access_token, decode_access_token

    token = create_access_token({"sub": "user1", "role": "adviser"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user1"


def test_jwt_has_expiry():
    from backend.core.security import create_access_token, decode_access_token

    token = create_access_token({"sub": "user1", "role": "adviser"})
    payload = decode_access_token(token)
    assert "exp" in payload


def test_decode_expired_token():
    from backend.core.security import decode_access_token

    # Create a token that's already expired
    expired_payload = {
        "sub": "user1",
        "role": "adviser",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, "testsecret", algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_decode_invalid_token():
    from backend.core.security import decode_access_token

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("not.a.token")
