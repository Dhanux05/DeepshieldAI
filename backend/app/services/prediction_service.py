from app.core.logging import get_logger
from app.ml.base import ModelUnavailableError
from app.ml.registry import registry
from app.models.prediction import Prediction
from app.repositories.document_repository import DocumentRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import (
    PredictionCreate,
    PredictionUpdate,
)

logger = get_logger(__name__)


class PredictionService:

    def __init__(
        self,
        prediction_repository: PredictionRepository,
        document_repository: DocumentRepository,
    ):
        self.prediction_repository = prediction_repository
        self.document_repository = document_repository

    def create_prediction(
        self,
        prediction_data: PredictionCreate,
    ):

        document = (
            self.document_repository.get_document_by_id(
                prediction_data.document_id
            )
        )

        if document is None:
            raise ValueError("Document not found.")

        prediction = Prediction(
            document_id=prediction_data.document_id,
            predicted_label=prediction_data.predicted_label,
            confidence_score=prediction_data.confidence_score,
            model_name=prediction_data.model_name,
            processing_status=prediction_data.processing_status,
            processing_time=prediction_data.processing_time,
        )

        return self.prediction_repository.create_prediction(
            prediction
        )

    def analyze_document(self, document_id: int) -> Prediction:
        """
        Run the real detector against an uploaded document and persist the
        result.

        A Prediction row is written up-front with status "Processing" so the
        record exists even if inference crashes — a failed analysis that
        leaves no trace is impossible to debug and impossible to audit.
        """
        document = self.document_repository.get_document_by_id(document_id)

        if document is None:
            raise ValueError("Document not found.")

        document_type = (
            document.document_type.type_name
            if document.document_type
            else "Unknown"
        )

        # Resolve the detector BEFORE writing a row, so an unsupported
        # modality doesn't litter the table with orphaned "Processing" rows.
        detector = registry.get_detector(document_type)

        prediction = self.prediction_repository.create_prediction(
            Prediction(
                document_id=document.id,
                predicted_label="Pending",
                confidence_score=0.0,
                model_name=detector.model_name,
                processing_status="Processing",
            )
        )

        try:
            result = detector.predict(document.file_path)

            prediction.predicted_label = result.label
            prediction.confidence_score = result.confidence
            prediction.model_name = result.model_name
            prediction.processing_time = result.processing_time
            prediction.processing_status = "Completed"

        except ModelUnavailableError:
            prediction.processing_status = "Failed"
            self.prediction_repository.update_prediction(prediction)
            raise

        except Exception as exc:
            prediction.processing_status = "Failed"
            self.prediction_repository.update_prediction(prediction)
            logger.exception("Inference failed for document %s", document_id)
            raise ValueError(f"Analysis failed: {exc}") from exc

        return self.prediction_repository.update_prediction(prediction)

    def get_prediction_by_id(
        self,
        prediction_id: int,
    ):

        prediction = (
            self.prediction_repository.get_prediction_by_id(
                prediction_id
            )
        )

        if prediction is None:
            raise ValueError("Prediction not found.")

        return prediction

    def get_predictions_by_document(
        self,
        document_id: int,
    ):

        return (
            self.prediction_repository.get_predictions_by_document(
                document_id
            )
        )

    def get_all_predictions(self, skip: int = 0, limit: int = 50):

        return (
            self.prediction_repository.get_all_predictions(skip, limit)
        )

    def update_prediction(
        self,
        prediction_id: int,
        updated_data: PredictionUpdate,
    ):

        prediction = (
            self.prediction_repository.get_prediction_by_id(
                prediction_id
            )
        )

        if prediction is None:
            raise ValueError("Prediction not found.")

        if updated_data.predicted_label is not None:
            prediction.predicted_label = (
                updated_data.predicted_label
            )

        if updated_data.confidence_score is not None:
            prediction.confidence_score = (
                updated_data.confidence_score
            )

        if updated_data.model_name is not None:
            prediction.model_name = (
                updated_data.model_name
            )

        if updated_data.processing_status is not None:
            prediction.processing_status = (
                updated_data.processing_status
            )

        if updated_data.processing_time is not None:
            prediction.processing_time = (
                updated_data.processing_time
            )

        return self.prediction_repository.update_prediction(
            prediction
        )

    def delete_prediction(
        self,
        prediction_id: int,
    ):

        prediction = (
            self.prediction_repository.get_prediction_by_id(
                prediction_id
            )
        )

        if prediction is None:
            raise ValueError("Prediction not found.")

        self.prediction_repository.delete_prediction(
            prediction
        )

        return {
            "message": "Prediction deleted successfully."
        }