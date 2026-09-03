from datetime import date, datetime

from pydantic import BaseModel


class PredictionCreate(BaseModel):
    document_id: int
    predicted_label: str
    confidence_score: float
    model_name: str
    processing_status: str = "Pending"
    processing_time: float | None = None


class PredictionUpdate(BaseModel):
    predicted_label: str | None = None
    confidence_score: float | None = None
    model_name: str | None = None
    processing_status: str | None = None
    processing_time: float | None = None


class PredictionResponse(BaseModel):
    id: int
    document_id: int
    predicted_label: str
    confidence_score: float
    model_name: str
    processing_status: str
    processing_time: float | None
    created_at: datetime

    class Config:
        from_attributes = True


# --------------------------------------------------------------- statistics


class CountItem(BaseModel):
    """A single (name, count) pair — used for label/status/model breakdowns."""

    name: str
    count: int


class DailyCount(BaseModel):
    """Predictions produced on a given calendar day."""

    day: date
    count: int


class PredictionStats(BaseModel):
    """
    Pre-aggregated dashboard figures.

    Every number here is computed by the database, not by fetching rows and
    counting them in Python (and certainly not in the browser). One request
    replaces six list calls, and the payload stays constant in size no matter
    how many predictions exist.
    """

    total_predictions: int
    total_documents: int
    total_reports: int
    total_knowledge_entries: int

    average_confidence: float | None
    average_processing_time: float | None

    label_breakdown: list[CountItem]
    status_breakdown: list[CountItem]
    model_breakdown: list[CountItem]
    document_type_breakdown: list[CountItem]

    daily_counts: list[DailyCount]
