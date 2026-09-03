from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.base import ModelUnavailableError
from app.repositories.explanation_repository import ExplanationRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.explanation import ExplanationResponse
from app.services.explanation_service import ExplanationService

router = APIRouter()


def get_explanation_service(
    db: Session = Depends(get_db),
):
    repository = ExplanationRepository(db)
    prediction_repository = PredictionRepository(db)

    return ExplanationService(
        repository,
        prediction_repository,
    )


@router.post(
    "/generate/{prediction_id}",
    response_model=ExplanationResponse,
)
def generate_explanation(
    prediction_id: int,
    method: str = Query(
        ...,
        description="'gradcam' (Image predictions) or 'shap' (Text/Review predictions).",
    ),
    service: ExplanationService = Depends(get_explanation_service),
):
    try:
        return service.generate_explanation(prediction_id, method)

    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/prediction/{prediction_id}",
    response_model=list[ExplanationResponse],
)
def get_explanations_by_prediction(
    prediction_id: int,
    service: ExplanationService = Depends(get_explanation_service),
):
    return service.get_by_prediction(prediction_id)


@router.get(
    "/{explanation_id}",
    response_model=ExplanationResponse,
)
def get_explanation(
    explanation_id: int,
    service: ExplanationService = Depends(get_explanation_service),
):
    try:
        return service.get_explanation_by_id(explanation_id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
