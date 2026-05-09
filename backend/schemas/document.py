from datetime import datetime

from pydantic import BaseModel


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    sensitivity_tier: int
    chunk_count: int
    ingested_at: datetime
    ingested_by: str
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
