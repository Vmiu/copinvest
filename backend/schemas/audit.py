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
