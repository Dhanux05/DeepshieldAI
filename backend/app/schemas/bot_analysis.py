from datetime import datetime

from pydantic import BaseModel


class BotAnalysisCreate(BaseModel):
    prediction_id: int
    question: str
    answer: str
    model_name: str


class BotAnalysisUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    model_name: str | None = None


class BotAnalysisResponse(BaseModel):
    id: int
    prediction_id: int
    question: str
    answer: str
    model_name: str
    created_at: datetime

    class Config:
        from_attributes = True