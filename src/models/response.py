from pydantic import BaseModel


class CitationSummary(BaseModel):
    valid: int
    invalid: int
    coverage: int
    confidence_level: str


class Citation(BaseModel):
    id: int
    source: str
    page: int
    chunk_id: str | int
    content: str
    chunk_text: str
    sentence: str
    position: int
    confidence: float
    valid: bool
    confidence_level: str


class QueryResponse(BaseModel):
    answer: str
    verified: bool
    session_id: str
    conversation_summary: str | None = None
    citation_summary: CitationSummary
    citations: list[Citation]
    retrieval_confidence: float
    citation_confidence: float
    confidence: float