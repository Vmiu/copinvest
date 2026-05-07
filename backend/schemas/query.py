from pydantic import BaseModel


class SourceCitation(BaseModel):
    doc_name: str
    section_title: str
    chunk_index: int


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    trace_id: str
    not_found: bool
    chunks_retrieved: int
    model_used: str
