import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import get_chunking_client, get_embedding_client, get_qdrant_client, require_role
from backend.models.enums import SensitivityTier
from backend.schemas.ingest import IngestResponse
from backend.services import ingestion_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["ingest"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    sensitivity_tier: SensitivityTier = Form(...),
    document_id: str | None = Form(None),
    current_user: dict = Depends(require_role("compliance")),
    db: AsyncSession = Depends(get_db),
    chunking_client: AsyncOpenAI = Depends(get_chunking_client),
    embedding_client: AsyncOpenAI = Depends(get_embedding_client),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = await ingestion_service.ingest_document(
            db=db,
            file_content=content,
            filename=file.filename or "unknown",
            sensitivity_tier=sensitivity_tier,
            user_id=current_user["user_id"],
            chunking_client=chunking_client,
            embedding_client=embedding_client,
            qdrant_client=qdrant_client,
            document_id=document_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    return result
