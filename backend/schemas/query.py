from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    doc_name: str
    section_title: str
    chunk_index: int


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(None, pattern=r'^[0-9a-f-]{36}$')


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    trace_id: str
    not_found: bool
    chunks_retrieved: int
    model_used: str
