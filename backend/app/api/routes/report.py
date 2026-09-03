from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.prediction_repository import (
    PredictionRepository,
)
from app.repositories.report_repository import (
    ReportRepository,
)
from app.schemas.report import (
    ReportCreate,
    ReportResponse,
    ReportUpdate,
)
from app.services.report_service import (
    ReportService,
)

router = APIRouter()


def get_report_service(
    db: Session = Depends(get_db),
):
    report_repository = ReportRepository(db)
    prediction_repository = PredictionRepository(db)

    return ReportService(
        report_repository,
        prediction_repository,
    )


@router.post(
    "/",
    response_model=ReportResponse,
)
def create_report(
    report: ReportCreate,
    service: ReportService = Depends(
        get_report_service
    ),
):
    try:
        return service.create_report(report)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[ReportResponse],
)
def get_all_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: ReportService = Depends(
        get_report_service
    ),
):
    return service.get_all_reports(skip, limit)


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    service: ReportService = Depends(
        get_report_service
    ),
):
    try:
        return service.get_report_by_id(
            report_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.get(
    "/prediction/{prediction_id}",
    response_model=list[ReportResponse],
)
def get_reports_by_prediction(
    prediction_id: int,
    service: ReportService = Depends(
        get_report_service
    ),
):
    return service.get_reports_by_prediction(
        prediction_id
    )


@router.put(
    "/{report_id}",
    response_model=ReportResponse,
)
def update_report(
    report_id: int,
    updated_data: ReportUpdate,
    service: ReportService = Depends(
        get_report_service
    ),
):
    try:
        return service.update_report(
            report_id,
            updated_data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.delete(
    "/{report_id}",
)
def delete_report(
    report_id: int,
    service: ReportService = Depends(
        get_report_service
    ),
):
    try:
        return service.delete_report(
            report_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )