import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import (
    get_chunking_client,
    get_generation_client,
    get_qdrant_client,
    require_role,
)
from backend.schemas.query import QueryRequest, QueryResponse
from backend.services import query_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: dict = Depends(require_role("adviser", "senior_adviser", "compliance")),
    db: AsyncSession = Depends(get_db),
    chunking_client: AsyncOpenAI = Depends(get_chunking_client),
    generation_client: AsyncOpenAI = Depends(get_generation_client),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
):
    try:
        result = await query_service.process_query(
            db=db,
            query=request.query,
            session_id=request.session_id,
            user_id=current_user["user_id"],
            user_role=current_user["role"],
            chunking_client=chunking_client,
            generation_client=generation_client,
            qdrant_client=qdrant_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    await db.commit()
    return QueryResponse(**result)
