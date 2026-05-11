import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.dependencies import require_role
from backend.repositories import audit_repo
from backend.schemas.audit import AuditDetailOut, AuditListResponse, SessionListResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = await audit_repo.list_sessions(db, offset=offset, limit=limit)
    return SessionListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/audit", response_model=AuditListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = await audit_repo.list_audits(
        db,
        offset=offset,
        limit=limit,
        user_id=user_id,
        session_id=session_id,
        date_from=date_from,
        date_to=date_to,
    )
    logger.info("audit_list_fetched", user=current_user["user_id"], total=total, page=page)
    return AuditListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/audit/{trace_id}", response_model=AuditDetailOut)
async def get_audit_detail(
    trace_id: str,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    record = await audit_repo.get_audit_by_id(db, trace_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    logger.info("audit_detail_fetched", user=current_user["user_id"], trace_id=trace_id)
    return record
