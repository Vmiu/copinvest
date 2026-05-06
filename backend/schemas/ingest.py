from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    sensitivity_tier: int
    chunk_count: int
    total_chars: int
    warnings: list[str]
    parse_duration_ms: int
    extraction_method: str
