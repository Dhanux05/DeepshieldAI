"""
Prediction pipeline tests.

These deliberately never touch the real trained detectors (Image/Audio/
Video/Text/Review/Bot) — a regression suite can't depend on ~800MB of model
weights being present on whichever machine runs `pytest`, and real
inference isn't what this layer's logic is responsible for anyway. Instead
`app.services.prediction_service.registry` is monkeypatched with a small
fake that satisfies the same `get_detector(document_type) -> BaseDetector`
contract (see app/ml/base.py, app/ml/registry.py) — the same technique this
project's Phase 11 design used to sandbox-verify the async pipeline before
it was ever deployed (see docs/ASYNC_PIPELINE.md).

Two call boundaries are tested separately, matching how the code is
actually split (see PredictionService.start_analysis / .run_analysis):

  * start_analysis() — synchronous: resolve the detector, create the
    "Processing" row, hand off to Celery. Tested through the real
    `POST /predictions/analyze/{id}` route, with `run_analysis_task.delay`
    monkeypatched so no real Celery worker or broker is needed.

  * run_analysis() — the actual inference-handling logic (the entire body
    of the old synchronous `analyze_document()`). Tested directly at the
    service layer, exactly like the Celery task itself calls it.
"""
import io

import app.tasks.prediction_tasks as prediction_tasks_module
from app.ml.base import DetectionResult, ModelUnavailableError
from app.models.prediction import Prediction
from app.repositories.document_repository import DocumentRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.prediction_service import PredictionService

from tests.conftest import register_and_login


class FakeDetector:
    """A BaseDetector stand-in with a scripted, deterministic outcome."""

    def __init__(self, model_name="fake-detector", should_crash=False):
        self.model_name = model_name
        self.is_ready = True
        self._should_crash = should_crash

    def predict(self, file_path: str) -> DetectionResult:
        if self._should_crash:
            raise RuntimeError("simulated inference crash")
        return DetectionResult(
            label="Genuine",
            confidence=0.87,
            probabilities={"Genuine": 0.87, "Deepfake": 0.13},
            model_name=self.model_name,
            processing_time=0.05,
        )


class FakeRegistry:
    """Satisfies ModelRegistry.get_detector()'s contract, nothing else."""

    def __init__(self, detectors: dict):
        self._detectors = detectors

    def get_detector(self, document_type: str):
        detector = self._detectors.get(document_type)
        if detector is None:
            raise ModelUnavailableError(f"No detector registered for '{document_type}'.")
        return detector


def _upload_document(client, headers, filename="photo.jpg", content_type="image/jpeg"):
    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": (filename, io.BytesIO(b"test bytes"), content_type)},
    )
    assert response.status_code == 200
    return response.json()["id"]


# --------------------------------------------------------------------------
# start_analysis() — through the real route, Celery dispatch mocked out
# --------------------------------------------------------------------------


def test_analyze_document_returns_202_and_dispatches_one_task(client, monkeypatch):
    dispatched_ids = []
    monkeypatch.setattr(
        prediction_tasks_module.run_analysis_task,
        "delay",
        lambda prediction_id: dispatched_ids.append(prediction_id),
    )
    monkeypatch.setattr(
        "app.services.prediction_service.registry",
        FakeRegistry({"Image": FakeDetector()}),
    )

    headers = register_and_login(client, "analyst@example.com")
    document_id = _upload_document(client, headers)

    response = client.post(f"/api/predictions/analyze/{document_id}", headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["processing_status"] == "Processing"
    assert body["predicted_label"] == "Pending"
    assert body["confidence_score"] == 0.0
    # The row really was created before the task was dispatched, and with
    # that row's own id — not a placeholder or the document's id.
    assert dispatched_ids == [body["id"]]


def test_analyze_unsupported_modality_returns_503_and_creates_no_row(
    client, monkeypatch, db_session
):
    monkeypatch.setattr(
        "app.services.prediction_service.registry",
        FakeRegistry({}),  # nothing registered for any modality
    )

    headers = register_and_login(client, "analyst2@example.com")
    document_id = _upload_document(client, headers, filename="clip.mp4", content_type="video/mp4")

    before = db_session.query(Prediction).count()
    response = client.post(f"/api/predictions/analyze/{document_id}", headers=headers)
    after = db_session.query(Prediction).count()

    assert response.status_code == 503
    # The detector is resolved BEFORE any row is written (see
    # start_analysis()'s docstring) specifically so a rejected request never
    # leaves an orphaned "Processing" row nobody will ever finish.
    assert after == before


def test_analyze_missing_document_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.prediction_service.registry",
        FakeRegistry({"Image": FakeDetector()}),
    )
    headers = register_and_login(client, "analyst3@example.com")

    response = client.post("/api/predictions/analyze/999999", headers=headers)
    assert response.status_code == 404


# --------------------------------------------------------------------------
# run_analysis() — the actual inference-handling logic, driven directly
# --------------------------------------------------------------------------


def _make_prediction_service(db_session) -> PredictionService:
    return PredictionService(PredictionRepository(db_session), DocumentRepository(db_session))


def _seed_document(db_session, document_type_name="Image"):
    from app.models.document import Document
    from app.models.document_type import DocumentType

    doc_type = (
        db_session.query(DocumentType)
        .filter(DocumentType.type_name == document_type_name)
        .first()
    )
    document = Document(
        file_name="a.jpg",
        original_file_name="a.jpg",
        file_path="images/a.jpg",
        file_size=10,
        mime_type="image/jpeg",
        uploaded_by=_seed_user(db_session).id,
        document_type_id=doc_type.id,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def _seed_user(db_session):
    from tests.conftest import make_user

    return make_user(db_session, email=f"svc-{id(db_session)}@example.com")


def test_run_analysis_happy_path_marks_completed(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.prediction_service.registry",
        FakeRegistry({"Image": FakeDetector(model_name="fake-image-v1")}),
    )

    document = _seed_document(db_session)
    prediction = Prediction(
        document_id=document.id,
        predicted_label="Pending",
        confidence_score=0.0,
        model_name="fake-image-v1",
        processing_status="Processing",
    )
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)

    service = _make_prediction_service(db_session)
    result = service.run_analysis(prediction.id)

    assert result.processing_status == "Completed"
    assert result.predicted_label == "Genuine"
    assert result.confidence_score == 0.87
    assert result.model_name == "fake-image-v1"


def test_run_analysis_marks_failed_when_detector_crashes(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.prediction_service.registry",
        FakeRegistry({"Image": FakeDetector(should_crash=True)}),
    )

    document = _seed_document(db_session)
    prediction = Prediction(
        document_id=document.id,
        predicted_label="Pending",
        confidence_score=0.0,
        model_name="fake-image-v1",
        processing_status="Processing",
    )
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)

    service = _make_prediction_service(db_session)

    try:
        service.run_analysis(prediction.id)
        raised = False
    except ValueError:
        raised = True

    assert raised, "a crashing detector must surface as a ValueError, not silently succeed"

    db_session.refresh(prediction)
    assert prediction.processing_status == "Failed"


def test_run_analysis_on_a_deleted_prediction_returns_none_without_raising(db_session):
    """
    The exact race this design guards against: the Celery task was
    dispatched for a row that no longer exists by the time a worker picks
    it up (e.g. the document/prediction was deleted in between). There is
    nothing to update and nothing to retry — see run_analysis()'s
    docstring.
    """
    service = _make_prediction_service(db_session)

    result = service.run_analysis(999999)

    assert result is None


def test_models_status_endpoint_reports_registry_shape(client):
    response = client.get("/api/predictions/models", headers=register_and_login(client, "reader@example.com"))
    assert response.status_code == 200
    body = response.json()
    assert "loaded" in body
    assert "detectors" in body
    assert "ready_count" in body
