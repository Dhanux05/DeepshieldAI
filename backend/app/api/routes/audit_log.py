from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.audit_log import (
    AuditLogCreate,
    AuditLogResponse,
    AuditLogUpdate,
)
from app.services.audit_log_service import AuditLogService

router = APIRouter()


def get_audit_log_service(
    db: Session = Depends(get_db),
):
    audit_repository = AuditLogRepository(db)
    user_repository = UserRepository(db)

    return AuditLogService(
        audit_repository,
        user_repository,
    )


@router.post(
    "/",
    response_model=AuditLogResponse,
)
def create_audit_log(
    audit_log: AuditLogCreate,
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    try:
        return service.create_audit_log(
            audit_log
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def get_all_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    return service.get_all_audit_logs(skip, limit)


@router.get(
    "/{audit_log_id}",
    response_model=AuditLogResponse,
)
def get_audit_log(
    audit_log_id: int,
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    try:
        return service.get_audit_log_by_id(
            audit_log_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.get(
    "/user/{user_id}",
    response_model=list[AuditLogResponse],
)
def get_logs_by_user(
    user_id: int,
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    return service.get_logs_by_user(
        user_id
    )


@router.put(
    "/{audit_log_id}",
    response_model=AuditLogResponse,
)
def update_audit_log(
    audit_log_id: int,
    updated_data: AuditLogUpdate,
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    try:
        return service.update_audit_log(
            audit_log_id,
            updated_data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.delete(
    "/{audit_log_id}",
)
def delete_audit_log(
    audit_log_id: int,
    service: AuditLogService = Depends(
        get_audit_log_service
    ),
):
    try:
        return service.delete_audit_log(
            audit_log_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )