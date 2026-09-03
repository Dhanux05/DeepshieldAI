from datetime import datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    prediction_id: int
    report_title: str
    report_summary: str
    report_path: str | None = None


class ReportUpdate(BaseModel):
    report_title: str | None = None
    report_summary: str | None = None
    report_path: str | None = None


class ReportResponse(BaseModel):
    id: int
    prediction_id: int
    report_title: str
    report_summary: str
    report_path: str | None
    created_at: datetime

    class Config:
        from_attributes = True