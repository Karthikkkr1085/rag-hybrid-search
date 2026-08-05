from pydantic import BaseModel


class QuerySettings(BaseModel):
    provider: str = "groq"
    model: str | None = None
    top_k: int = 8
    temperature: float = 0.2
    max_tokens: int = 512
    enable_cross_encoder: bool = True
    enable_bm25: bool = True
    enable_vector_search: bool = True
    enable_hybrid_search: bool = True
    enable_rrf: bool = True


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None
    settings: QuerySettings | None = None