from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from backend.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Application-lifetime singletons — initialised in lifespan (main.py)
_chunking_client: AsyncOpenAI | None = None
_openrouter_client: AsyncOpenAI | None = None
_qdrant_client: QdrantClient | None = None


def init_clients(chunking_client: AsyncOpenAI, openrouter_client: AsyncOpenAI, qdrant_client: QdrantClient) -> None:
    global _chunking_client, _openrouter_client, _qdrant_client
    _chunking_client = chunking_client
    _openrouter_client = openrouter_client
    _qdrant_client = qdrant_client


def get_chunking_client() -> AsyncOpenAI:
    if _chunking_client is None:
        raise RuntimeError("Chunking client not initialised")
    return _chunking_client


def get_openrouter_client() -> AsyncOpenAI:
    if _openrouter_client is None:
        raise RuntimeError("OpenRouter client not initialised")
    return _openrouter_client


def get_embedding_client() -> AsyncOpenAI:
    """Backwards-compat alias — returns openrouter client."""
    return get_openrouter_client()


def get_openai_client() -> AsyncOpenAI:
    """Backwards-compat alias — returns chunking client."""
    return get_chunking_client()


def get_qdrant_client() -> QdrantClient:
    if _qdrant_client is None:
        raise RuntimeError("Qdrant client not initialised")
    return _qdrant_client


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"user_id": user_id, "role": role}


def require_role(*allowed_roles: str):
    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' not authorized",
            )
        return current_user
    return _check
