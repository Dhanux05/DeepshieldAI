"""
Celery task(s) for Phase 11's async prediction pipeline.

Kept deliberately thin: this module's only job is process/session plumbing
(open a DB session Celery can own, hand off to the same service-layer logic
the old synchronous endpoint used, close the session). All the actual
"how do I run a detector and interpret its result" logic still lives in
`PredictionService.run_analysis()` — the task does not reimplement it, so
there is exactly one place that logic can go wrong, not two.
"""

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories.document_repository import DocumentRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.prediction_service import PredictionService

logger = get_logger(__name__)


@celery_app.task(name="predictions.run_analysis", bind=True, max_retries=0)
def run_analysis_task(self, prediction_id: int) -> None:
    """
    Execute the detector for an already-created "Processing" Prediction row.

    A Celery task has no FastAPI request to piggy-back a DB session on — it
    opens and closes its own here, exactly like `get_db()` does per-request,
    just without the `yield`.

    `max_retries=0`: an inference failure (missing weights, corrupt file,
    unsupported input) will not fix itself on retry — it should surface as
    a "Failed" prediction the user can see immediately, not silently retry
    and delay that visibility.
    """
    db = SessionLocal()
    try:
        service = PredictionService(
            PredictionRepository(db),
            DocumentRepository(db),
        )
        service.run_analysis(prediction_id)
    except Exception:
        # run_analysis() already persists "Failed" on the row itself before
        # re-raising (see its docstring) — this log exists so the failure is
        # also visible in the worker's own logs, not just the database.
        logger.exception("Celery task failed for prediction_id=%s", prediction_id)
    finally:
        db.close()
