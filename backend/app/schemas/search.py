from uuid import UUID
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    job_id: UUID
    query: str = Field(..., min_length=3, max_length=512)
    top_k: int = Field(default=5, ge=1, le=20)
    speaker_filter: str | None = None


class GlobalSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=512)
    top_k: int = Field(default=10, ge=1, le=50)
    user_id: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    job_id: str
    chunk_index: int
    text: str
    speaker_id: str | None
    start_s: float
    end_s: float
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    cached: bool
    latency_ms: float


class ContradictionItem(BaseModel):
    id: UUID
    chunk_a: dict
    chunk_b: dict
    score: float
    label: str
    explanation: str | None

    model_config = {"from_attributes": True}


class ContradictionResponse(BaseModel):
    job_id: UUID
    contradictions: list[ContradictionItem]
    total: int
