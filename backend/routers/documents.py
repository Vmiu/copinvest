import json

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.repositories import document_repo
from backend.schemas.document import DocumentListItem, DocumentListResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    document_type: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    docs = await document_repo.list_documents(db, document_type=document_type, jurisdiction=jurisdiction)
    items = []
    for d in docs:
        data = {c.key: getattr(d, c.key) for c in d.__table__.columns}
        data["product_codes"] = json.loads(d.product_codes) if d.product_codes else []
        items.append(DocumentListItem.model_validate(data))
    logger.info("documents_list_fetched", user=current_user["user_id"], count=len(items))
    return DocumentListResponse(items=items, total=len(items))
