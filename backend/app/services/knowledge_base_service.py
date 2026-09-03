from app.models.knowledge_base import KnowledgeBase
from app.repositories.document_repository import (
    DocumentRepository,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
)


class KnowledgeBaseService:

    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        document_repository: DocumentRepository,
    ):
        self.repository = repository
        self.document_repository = document_repository

    def create(
        self,
        data: KnowledgeBaseCreate,
    ):

        document = (
            self.document_repository.get_document_by_id(
                data.document_id
            )
        )

        if document is None:
            raise ValueError(
                "Document not found."
            )

        knowledge = KnowledgeBase(
            document_id=data.document_id,
            vector_id=data.vector_id,
            embedding_model=data.embedding_model,
            chunk_count=data.chunk_count,
            index_status=data.index_status,
        )

        return self.repository.create(
            knowledge
        )

    def get_by_id(
        self,
        knowledge_id: int,
    ):

        knowledge = self.repository.get_by_id(
            knowledge_id
        )

        if knowledge is None:
            raise ValueError(
                "Knowledge Base entry not found."
            )

        return knowledge

    def get_all(self, skip: int = 0, limit: int = 50):

        return self.repository.get_all(skip, limit)

    def get_by_document(
        self,
        document_id: int,
    ):

        return self.repository.get_by_document(
            document_id
        )

    def update(
        self,
        knowledge_id: int,
        updated_data: KnowledgeBaseUpdate,
    ):

        knowledge = self.repository.get_by_id(
            knowledge_id
        )

        if knowledge is None:
            raise ValueError(
                "Knowledge Base entry not found."
            )

        if updated_data.vector_id is not None:
            knowledge.vector_id = updated_data.vector_id

        if updated_data.embedding_model is not None:
            knowledge.embedding_model = updated_data.embedding_model

        if updated_data.chunk_count is not None:
            knowledge.chunk_count = updated_data.chunk_count

        if updated_data.index_status is not None:
            knowledge.index_status = updated_data.index_status

        return self.repository.update(
            knowledge
        )

    def delete(
        self,
        knowledge_id: int,
    ):

        knowledge = self.repository.get_by_id(
            knowledge_id
        )

        if knowledge is None:
            raise ValueError(
                "Knowledge Base entry not found."
            )

        self.repository.delete(
            knowledge
        )

        return {
            "message": "Knowledge Base entry deleted successfully."
        }