from datetime import datetime

from pydantic import BaseModel


class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    resource: str
    details: str | None = None
    ip_address: str | None = None


class AuditLogUpdate(BaseModel):
    action: str | None = None
    resource: str | None = None
    details: str | None = None
    ip_address: str | None = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    resource: str
    details: str | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True