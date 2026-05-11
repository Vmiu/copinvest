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
    document_type: str | None = None
    language: str | None = None
    jurisdiction: str | None = None
    product_codes: list[str] = []
    parent_doc_title: str | None = None
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
