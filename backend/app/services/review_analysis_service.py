from app.models.review_analysis import ReviewAnalysis
from app.repositories.prediction_repository import (
    PredictionRepository,
)
from app.repositories.review_analysis_repository import (
    ReviewAnalysisRepository,
)
from app.schemas.review_analysis import (
    ReviewAnalysisCreate,
    ReviewAnalysisUpdate,
)


class ReviewAnalysisService:

    def __init__(
        self,
        repository: ReviewAnalysisRepository,
        prediction_repository: PredictionRepository,
    ):
        self.repository = repository
        self.prediction_repository = prediction_repository

    def create_review_analysis(
        self,
        data: ReviewAnalysisCreate,
    ):

        prediction = (
            self.prediction_repository
            .get_prediction_by_id(
                data.prediction_id
            )
        )

        if prediction is None:
            raise ValueError(
                "Prediction not found."
            )

        review = ReviewAnalysis(
            prediction_id=data.prediction_id,
            summary=data.summary,
            evidence=data.evidence,
            recommendation=data.recommendation,
            model_name=data.model_name,
        )

        return self.repository.create_review_analysis(
            review
        )

    def get_review_analysis_by_id(
        self,
        review_id: int,
    ):

        review = (
            self.repository
            .get_review_analysis_by_id(
                review_id
            )
        )

        if review is None:
            raise ValueError(
                "Review analysis not found."
            )

        return review

    def get_all_review_analyses(self, skip: int = 0, limit: int = 50):

        return self.repository.get_all_review_analyses(skip, limit)

    def get_by_prediction(
        self,
        prediction_id: int,
    ):

        return self.repository.get_by_prediction(
            prediction_id
        )

    def update_review_analysis(
        self,
        review_id: int,
        updated_data: ReviewAnalysisUpdate,
    ):

        review = (
            self.repository
            .get_review_analysis_by_id(
                review_id
            )
        )

        if review is None:
            raise ValueError(
                "Review analysis not found."
            )

        if updated_data.summary is not None:
            review.summary = updated_data.summary

        if updated_data.evidence is not None:
            review.evidence = updated_data.evidence

        if updated_data.recommendation is not None:
            review.recommendation = (
                updated_data.recommendation
            )

        if updated_data.model_name is not None:
            review.model_name = (
                updated_data.model_name
            )

        return self.repository.update_review_analysis(
            review
        )

    def delete_review_analysis(
        self,
        review_id: int,
    ):

        review = (
            self.repository
            .get_review_analysis_by_id(
                review_id
            )
        )

        if review is None:
            raise ValueError(
                "Review analysis not found."
            )

        self.repository.delete_review_analysis(
            review
        )

        return {
            "message": "Review analysis deleted successfully."
        }