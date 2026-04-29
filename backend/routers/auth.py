from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import verify_password, create_access_token
from backend.repositories.user_repo import get_user_by_email
from backend.schemas.auth import TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    role = user.role.value if hasattr(user.role, "value") else user.role
    token = create_access_token({"sub": user.id, "role": role})
    return TokenResponse(access_token=token)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
