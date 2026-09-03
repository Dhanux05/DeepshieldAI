from app.models.bot_analysis import BotAnalysis
from app.repositories.bot_analysis_repository import (
    BotAnalysisRepository,
)
from app.repositories.prediction_repository import (
    PredictionRepository,
)
from app.schemas.bot_analysis import (
    BotAnalysisCreate,
    BotAnalysisUpdate,
)


class BotAnalysisService:

    def __init__(
        self,
        repository: BotAnalysisRepository,
        prediction_repository: PredictionRepository,
    ):
        self.repository = repository
        self.prediction_repository = prediction_repository

    def create_bot_analysis(
        self,
        data: BotAnalysisCreate,
    ):

        prediction = (
            self.prediction_repository.get_prediction_by_id(
                data.prediction_id
            )
        )

        if prediction is None:
            raise ValueError(
                "Prediction not found."
            )

        analysis = BotAnalysis(
            prediction_id=data.prediction_id,
            question=data.question,
            answer=data.answer,
            model_name=data.model_name,
        )

        return self.repository.create_bot_analysis(
            analysis
        )

    def get_bot_analysis_by_id(
        self,
        analysis_id: int,
    ):

        analysis = (
            self.repository.get_bot_analysis_by_id(
                analysis_id
            )
        )

        if analysis is None:
            raise ValueError(
                "Bot analysis not found."
            )

        return analysis

    def get_all_bot_analyses(self, skip: int = 0, limit: int = 50):

        return self.repository.get_all_bot_analyses(skip, limit)

    def get_by_prediction(
        self,
        prediction_id: int,
    ):

        return self.repository.get_by_prediction(
            prediction_id
        )

    def update_bot_analysis(
        self,
        analysis_id: int,
        updated_data: BotAnalysisUpdate,
    ):

        analysis = (
            self.repository.get_bot_analysis_by_id(
                analysis_id
            )
        )

        if analysis is None:
            raise ValueError(
                "Bot analysis not found."
            )

        if updated_data.question is not None:
            analysis.question = updated_data.question

        if updated_data.answer is not None:
            analysis.answer = updated_data.answer

        if updated_data.model_name is not None:
            analysis.model_name = updated_data.model_name

        return self.repository.update_bot_analysis(
            analysis
        )

    def delete_bot_analysis(
        self,
        analysis_id: int,
    ):

        analysis = (
            self.repository.get_bot_analysis_by_id(
                analysis_id
            )
        )

        if analysis is None:
            raise ValueError(
                "Bot analysis not found."
            )

        self.repository.delete_bot_analysis(
            analysis
        )

        return {
            "message": "Bot analysis deleted successfully."
        }