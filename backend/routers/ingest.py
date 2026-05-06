import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.models.enums import SensitivityTier
from backend.schemas.ingest import IngestResponse
from backend.services import ingestion_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    sensitivity_tier: SensitivityTier = Form(...),
    document_id: str | None = Form(None),
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = await ingestion_service.ingest_document(
            db=db,
            file_content=content,
            filename=file.filename or "unknown",
            sensitivity_tier=sensitivity_tier,
            user_id=current_user["user_id"],
            document_id=document_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    return result
