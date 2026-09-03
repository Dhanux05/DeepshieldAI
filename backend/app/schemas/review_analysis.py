from datetime import datetime

from pydantic import BaseModel


class ReviewAnalysisCreate(BaseModel):
    prediction_id: int
    summary: str
    evidence: str
    recommendation: str
    model_name: str


class ReviewAnalysisUpdate(BaseModel):
    summary: str | None = None
    evidence: str | None = None
    recommendation: str | None = None
    model_name: str | None = None


class ReviewAnalysisResponse(BaseModel):
    id: int
    prediction_id: int
    summary: str
    evidence: str
    recommendation: str
    model_name: str
    created_at: datetime

    class Config:
        from_attributes = True