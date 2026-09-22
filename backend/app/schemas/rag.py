from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class RagPassage(BaseModel):
    text: str
    source: str
    chunk_index: int
    relevance: float


class RagQueryResponse(BaseModel):
    question: str
    results: list[RagPassage]


class RagSyncResponse(BaseModel):
    synced: list[str]
    skipped: list[str]
    removed_stale: list[str]
