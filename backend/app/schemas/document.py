from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    description: Optional[str] = None
    document_type_id: int


class DocumentUpdate(BaseModel):
    description: Optional[str] = None
    document_type_id: Optional[int] = None


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    original_file_name: str
    file_path: str
    file_size: int
    mime_type: str
    description: Optional[str]
    uploaded_at: datetime
    uploaded_by: int
    document_type_id: int
    # Resolved type name (e.g. "Account"), not just the FK id — a `.json`
    # upload is otherwise indistinguishable from a plain Text document on
    # the frontend. Backed by Document.document_type_name, a plain Python
    # property; from_attributes reads it like any other attribute.
    document_type_name: str

    class Config:
        from_attributes = True