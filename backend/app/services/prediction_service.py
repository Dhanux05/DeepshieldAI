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

    def start_analysis(self, document_id: int) -> Prediction:
        """
        Create a "Processing" Prediction row and hand the real work to a
        Celery worker, returning immediately.

        Phase 11's async replacement for what used to be a single
        synchronous `analyze_document()` that ran the model inline and made
        the caller wait for it. That method's inference logic hasn't
        changed — it now lives in `run_analysis()` below, unchanged, just no
        longer called directly from the request handler. See
        docs/ASYNC_PIPELINE.md for the full design.

        The row is still created here, synchronously, for the same reason
        the original code did: a resolvable detector must exist BEFORE a
        row is created, so an unsupported modality doesn't litter the table
        with orphaned rows nobody will ever finish, and the caller gets an
        immediate 503 instead of a task queued only to fail instantly.
        Everything after that — the actual inference — happens in a
        different process.
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

        # Imported here, not at module level: this keeps PredictionService
        # importable (and unit-testable with a fake registry) without
        # Celery/Redis configured at all — only this one call site actually
        # needs to dispatch a task.
        from app.tasks.prediction_tasks import run_analysis_task

        run_analysis_task.delay(prediction.id)

        return prediction

    def run_analysis(self, prediction_id: int) -> Prediction | None:
        """
        Do the actual inference for an existing "Processing" Prediction row.

        This is the entire body of what used to be inside the synchronous
        `analyze_document()` — unchanged logic. It's invoked from two
        places: the Celery task (`app/tasks/prediction_tasks.py`) in normal
        operation, and directly by anything that wants to exercise this
        logic with Celery's `task_always_eager` (no real broker needed, see
        docs/ASYNC_PIPELINE.md). Both call sites get identical behaviour
        because there is only one implementation.
        """
        prediction = self.prediction_repository.get_prediction_by_id(
            prediction_id
        )

        if prediction is None:
            # The row this task was dispatched for is gone (e.g. deleted
            # between dispatch and execution) — nothing to update, nothing
            # to retry.
            logger.warning(
                "run_analysis: prediction %s no longer exists", prediction_id
            )
            return None

        document = self.document_repository.get_document_by_id(
            prediction.document_id
        )

        if document is None:
            prediction.processing_status = "Failed"
            return self.prediction_repository.update_prediction(prediction)

        document_type = (
            document.document_type.type_name
            if document.document_type
            else "Unknown"
        )

        try:
            detector = registry.get_detector(document_type)
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
            logger.exception(
                "Inference failed for prediction %s", prediction_id
            )
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