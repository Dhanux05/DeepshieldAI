from sqlalchemy.orm import Session

from app.models.document_type import DocumentType
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeUpdate,
)


class DocumentTypeRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_document_type(
        self,
        document_type: DocumentTypeCreate
    ) -> DocumentType:

        new_document_type = DocumentType(
            type_name=document_type.type_name,
            description=document_type.description
        )

        self.db.add(new_document_type)
        self.db.commit()
        self.db.refresh(new_document_type)

        return new_document_type

    def get_document_type_by_id(
        self,
        document_type_id: int
    ) -> DocumentType | None:

        return (
            self.db.query(DocumentType)
            .filter(DocumentType.id == document_type_id)
            .first()
        )

    def get_document_type_by_name(
        self,
        type_name: str
    ) -> DocumentType | None:

        return (
            self.db.query(DocumentType)
            .filter(DocumentType.type_name == type_name)
            .first()
        )

    def get_all_document_types(self):

        return (
            self.db.query(DocumentType)
            .order_by(DocumentType.id)
            .all()
        )

    def update_document_type(
        self,
        document_type: DocumentType,
        updated_data: DocumentTypeUpdate
    ) -> DocumentType:

        if updated_data.type_name is not None:
            document_type.type_name = updated_data.type_name

        if updated_data.description is not None:
            document_type.description = updated_data.description

        self.db.commit()
        self.db.refresh(document_type)

        return document_type

    def delete_document_type(
        self,
        document_type: DocumentType
    ) -> None:

        self.db.delete(document_type)
        self.db.commit()