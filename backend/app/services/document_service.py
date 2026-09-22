from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_type_repository import (
    DocumentTypeRepository,
)
from app.schemas.document import DocumentUpdate
from app.utils.file_storage import FileStorage
from app.utils.file_type import FileType


class DocumentService:

    def __init__(self, db: Session):
        self.document_repository = DocumentRepository(db)
        self.document_type_repository = DocumentTypeRepository(db)

    def upload_document(
        self,
        file: UploadFile,
        description: str | None,
        current_user: User,
        document_type_override: str | None = None,
    ) -> Document:
        """
        `document_type_override` exists for modalities whose input isn't
        identifiable by file extension alone. Every media modality
        (Image/Audio/Video/Text/Review) is inferred from the extension via
        `FileType`, same as always. Account is the exception: it's a plain
        `.json` upload — the same extension `.json`/`.csv` already fall
        under `FileType`'s "Text" bucket — so the frontend's "Analyze an
        Account" form passes `document_type="Account"` explicitly instead of
        relying on the extension. Omitting the override preserves today's
        behaviour exactly for every existing caller.
        """

        if document_type_override:
            document_type = (
                self.document_type_repository
                .get_document_type_by_name(document_type_override)
            )

            if document_type is None:
                raise ValueError(
                    f"Document type '{document_type_override}' not found."
                )

            folder = document_type_override.lower() + "s"

        else:
            document_type_name = FileType.get_document_type(
                file.filename
            )

            folder = FileType.get_upload_folder(
                file.filename
            )

            document_type = (
                self.document_type_repository
                .get_document_type_by_name(document_type_name)
            )

            if document_type is None:
                raise ValueError(
                    f"Document type '{document_type_name}' not found."
                )

        unique_filename, file_path = FileStorage.save_file(
            file=file,
            folder=folder
        )

        document = Document(
            file_name=unique_filename,
            original_file_name=file.filename,
            file_path=file_path,
            file_size=file.size if file.size else 0,
            mime_type=file.content_type or "",
            description=description,
            uploaded_by=current_user.id,
            document_type_id=document_type.id,
        )

        return self.document_repository.create_document(document)

    def get_document_by_id(
        self,
        document_id: int
    ) -> Document:

        document = (
            self.document_repository
            .get_document_by_id(document_id)
        )

        if document is None:
            raise ValueError("Document not found.")

        return document

    def get_all_documents(self, skip: int = 0, limit: int = 50):
        return self.document_repository.get_all_documents(skip, limit)

    def get_documents_by_user(
        self,
        user_id: int
    ):
        return self.document_repository.get_documents_by_user(
            user_id
        )

    def update_document(
        self,
        document_id: int,
        updated_data: DocumentUpdate
    ):

        document = (
            self.document_repository
            .get_document_by_id(document_id)
        )

        if document is None:
            raise ValueError("Document not found.")

        if updated_data.description is not None:
            document.description = updated_data.description

        if updated_data.document_type_id is not None:

            document_type = (
                self.document_type_repository
                .get_document_type_by_id(
                    updated_data.document_type_id
                )
            )

            if document_type is None:
                raise ValueError(
                    "Document type does not exist."
                )

            document.document_type_id = (
                updated_data.document_type_id
            )

        return self.document_repository.update_document(
            document
        )

    def delete_document(
        self,
        document_id: int
    ):

        document = (
            self.document_repository
            .get_document_by_id(document_id)
        )

        if document is None:
            raise ValueError("Document not found.")

        FileStorage.delete_file(document.file_path)

        self.document_repository.delete_document(
            document
        )

        return {
            "message": "Document deleted successfully."
        }
