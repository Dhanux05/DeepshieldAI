from app.repositories.document_type_repository import (
    DocumentTypeRepository,
)
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeUpdate,
)


class DocumentTypeService:

    def __init__(self, repository: DocumentTypeRepository):
        self.repository = repository

    def create_document_type(
        self,
        document_type: DocumentTypeCreate
    ):

        # Check if document type already exists
        existing_document_type = (
            self.repository.get_document_type_by_name(
                document_type.type_name
            )
        )

        if existing_document_type:
            raise ValueError(
                "Document type already exists."
            )

        return self.repository.create_document_type(
            document_type
        )

    def get_document_type_by_id(
        self,
        document_type_id: int
    ):

        document_type = (
            self.repository.get_document_type_by_id(
                document_type_id
            )
        )

        if not document_type:
            raise ValueError(
                "Document type not found."
            )

        return document_type

    def get_all_document_types(self):

        return self.repository.get_all_document_types()

    def update_document_type(
        self,
        document_type_id: int,
        updated_data: DocumentTypeUpdate
    ):

        document_type = (
            self.repository.get_document_type_by_id(
                document_type_id
            )
        )

        if not document_type:
            raise ValueError(
                "Document type not found."
            )

        if updated_data.type_name:

            existing = (
                self.repository.get_document_type_by_name(
                    updated_data.type_name
                )
            )

            if (
                existing
                and existing.id != document_type.id
            ):
                raise ValueError(
                    "Document type already exists."
                )

        return self.repository.update_document_type(
            document_type,
            updated_data
        )

    def delete_document_type(
        self,
        document_type_id: int
    ):

        document_type = (
            self.repository.get_document_type_by_id(
                document_type_id
            )
        )

        if not document_type:
            raise ValueError(
                "Document type not found."
            )

        self.repository.delete_document_type(
            document_type
        )

        return {
            "message": "Document type deleted successfully."
        }
