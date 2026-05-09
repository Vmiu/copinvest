from pydantic import BaseModel
from datetime import datetime

from backend.models.enums import AuditStatus, AdviserAction


class AuditRecordOut(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    channel: str
    query_text: str
    status: AuditStatus
    sensitivity_tier_accessed: int | None = None
    model_used: str | None = None
    adviser_action: AdviserAction | None = None

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    user_id: str
    start_time: datetime
    end_time: datetime | None = None

    model_config = {"from_attributes": True}


class AuditListItem(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    channel: str
    query_text: str
    status: AuditStatus
    adviser_action: AdviserAction | None = None
    not_found: bool | None = None
    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    items: list[AuditListItem]
    total: int
    page: int
    limit: int


class AuditDetailOut(BaseModel):
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    channel: str
    query_text: str
    rewritten_query: str | None = None
    status: AuditStatus
    retrieved_chunks: str | None = None   # JSON string — frontend must JSON.parse()
    sensitivity_tier_accessed: int | None = None
    prompt_sent: str | None = None
    llm_response: str | None = None
    model_used: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    adviser_action: AdviserAction | None = None
    adviser_edited: bool | None = None
    final_response: str | None = None
    not_found: bool | None = None
    chunks_passed_rerank: int | None = None
    model_config = {"from_attributes": True}
