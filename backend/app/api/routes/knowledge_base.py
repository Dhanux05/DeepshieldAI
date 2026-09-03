from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.document_repository import (
    DocumentRepository,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base_service import (
    KnowledgeBaseService,
)

router = APIRouter()


def get_knowledge_base_service(
    db: Session = Depends(get_db),
):
    repository = KnowledgeBaseRepository(db)
    document_repository = DocumentRepository(db)

    return KnowledgeBaseService(
        repository,
        document_repository,
    )


@router.post(
    "/",
    response_model=KnowledgeBaseResponse,
)
def create_knowledge(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    try:
        return service.create(data)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[KnowledgeBaseResponse],
)
def get_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    return service.get_all(skip, limit)


@router.get(
    "/{knowledge_id}",
    response_model=KnowledgeBaseResponse,
)
def get_by_id(
    knowledge_id: int,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    try:
        return service.get_by_id(
            knowledge_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.get(
    "/document/{document_id}",
    response_model=list[KnowledgeBaseResponse],
)
def get_by_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    return service.get_by_document(
        document_id
    )


@router.put(
    "/{knowledge_id}",
    response_model=KnowledgeBaseResponse,
)
def update(
    knowledge_id: int,
    updated_data: KnowledgeBaseUpdate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    try:
        return service.update(
            knowledge_id,
            updated_data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.delete(
    "/{knowledge_id}",
)
def delete(
    knowledge_id: int,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
):
    try:
        return service.delete(
            knowledge_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )