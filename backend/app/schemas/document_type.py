from pydantic import BaseModel


class DocumentTypeBase(BaseModel):
    type_name: str
    description: str | None = None


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    type_name: str | None = None
    description: str | None = None


class DocumentTypeResponse(DocumentTypeBase):
    id: int

    class Config:
        from_attributes = True