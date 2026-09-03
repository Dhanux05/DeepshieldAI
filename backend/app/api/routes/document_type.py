from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.document_type_repository import (
    DocumentTypeRepository,
)
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeResponse,
    DocumentTypeUpdate,
)
from app.services.document_type_service import DocumentTypeService

router = APIRouter()


def get_document_type_service(
    db: Session = Depends(get_db),
):
    repository = DocumentTypeRepository(db)
    return DocumentTypeService(repository)


@router.post(
    "/",
    response_model=DocumentTypeResponse,
)
def create_document_type(
    document_type: DocumentTypeCreate,
    service: DocumentTypeService = Depends(
        get_document_type_service
    ),
):
    try:
        return service.create_document_type(
            document_type
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[DocumentTypeResponse],
)
def get_all_document_types(
    service: DocumentTypeService = Depends(
        get_document_type_service
    ),
):
    return service.get_all_document_types()


@router.get(
    "/{document_type_id}",
    response_model=DocumentTypeResponse,
)
def get_document_type(
    document_type_id: int,
    service: DocumentTypeService = Depends(
        get_document_type_service
    ),
):
    try:
        return service.get_document_type_by_id(
            document_type_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.put(
    "/{document_type_id}",
    response_model=DocumentTypeResponse,
)
def update_document_type(
    document_type_id: int,
    updated_data: DocumentTypeUpdate,
    service: DocumentTypeService = Depends(
        get_document_type_service
    ),
):
    try:
        return service.update_document_type(
            document_type_id,
            updated_data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.delete(
    "/{document_type_id}",
)
def delete_document_type(
    document_type_id: int,
    service: DocumentTypeService = Depends(
        get_document_type_service
    ),
):
    try:
        return service.delete_document_type(
            document_type_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
