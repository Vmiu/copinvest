import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.repositories import document_repo
from backend.schemas.document import DocumentListResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
):
    items = await document_repo.list_documents(db)
    logger.info("documents_list_fetched", user=current_user["user_id"], count=len(items))
    return DocumentListResponse(items=items, total=len(items))
