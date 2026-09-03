import os
import time
from pathlib import Path

from app.core.logging import get_logger
from app.ml.base import BaseDetector, DetectionResult, ModelUnavailableError
from app.ml.preprocessing import preprocess_file

logger = get_logger(__name__)


class ImageDetector(BaseDetector):
    """
    Keras/MobileNetV2 binary deepfake classifier.

    Architecture recovered from the trained artefact:

        Input(224, 224, 3)
          -> MobileNetV2 (imagenet backbone, include_top=False)
          -> GlobalAveragePooling2D
          -> Dropout -> Dense(128, relu) -> Dropout
          -> Dense(1, sigmoid)          # 2,750,277 params total

    A single sigmoid unit means the raw output is P(positive class). Which
    physical class is "positive" is NOT stored in the file — Keras discards
    the directory->index mapping — so `positive_label` is configuration.
    Get it wrong and every verdict is exactly inverted.

    KERAS BACKEND: this project's Python is 3.14, and `tensorflow-cpu` has
    no published wheel for it yet — installing it fails outright, not just
    slowly. Keras 3 was built to be backend-agnostic (TensorFlow, JAX, or
    PyTorch can all execute the same saved graph), and the `.keras` archive
    format stores weights in a backend-portable way specifically so this
    substitution is safe for standard architectures like MobileNetV2. Since
    `torch` is already a hard requirement for the Audio detector and DOES
    have Python 3.14 wheels, `load()` below selects the PyTorch backend for
    Keras instead of waiting on a TensorFlow wheel that may not land for
    months. `requirements/ml.txt` reflects this — no `tensorflow` install
    needed at all.
    """

    modality = "Image"

    def __init__(
        self,
        weights_path: str,
        input_size: int = 224,
        preprocess_mode: str = "mobilenet_v2",
        positive_label: str = "Genuine",
        negative_label: str = "Deepfake",
        threshold: float = 0.5,
    ):
        self.weights_path = weights_path
        self.input_size = input_size
        self.preprocess_mode = preprocess_mode
        self.positive_label = positive_label
        self.negative_label = negative_label
        self.threshold = threshold

        self._model = None
        self._name = "mobilenetv2_deepshield"
        self._load_error: str | None = None

    # ------------------------------------------------------------ contract
    @property
    def model_name(self) -> str:
        return self._name

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def underlying_model(self):
        """
        The raw loaded Keras model — exposed read-only for xai/gradcam.py,
        which needs to build a second functional model over the same
        layers (input -> last conv layer + input -> final output) to get
        at intermediate activations. Nothing outside app/ml and xai should
        need this; predict() below is still the real public contract.
        """
        return self._model

    def load(self) -> None:
        """
        Load the .keras archive once, at startup.

        Loading per request would add seconds of latency and blow up memory
        under any concurrency. Failures are captured rather than raised so a
        missing model file cannot stop the API from booting — the rest of the
        product still works, and /predictions/models reports why.
        """
        path = Path(self.weights_path)

        if not path.exists():
            self._load_error = f"Weights not found at {path}"
            logger.warning("ImageDetector: %s", self._load_error)
            return

        # Must be set before Keras is first imported anywhere in the
        # process — Keras reads KERAS_BACKEND at import time and cannot
        # switch backends afterward. setdefault() means an operator who DOES
        # have a working TensorFlow install (e.g. a different Python
        # version) can still override this via a real environment variable.
        os.environ.setdefault("KERAS_BACKEND", "torch")

        try:
            # Imported lazily: the API container should not need Keras at
            # all just to serve CRUD endpoints.
            import keras
        except ImportError:
            self._load_error = (
                "Keras is not installed. "
                "Install requirements/ml.txt to enable image inference."
            )
            logger.warning("ImageDetector: %s", self._load_error)
            return

        try:
            self._model = keras.saving.load_model(str(path), compile=False)
        except Exception as exc:  # noqa: BLE001 - surfaced via /models
            self._load_error = f"{type(exc).__name__}: {exc}"
            logger.exception("ImageDetector failed to load %s", path)
            return

        self._name = getattr(self._model, "name", self._name)
        logger.info(
            "ImageDetector ready — %s (%s params, %s preprocessing)",
            self._name,
            f"{self._model.count_params():,}",
            self.preprocess_mode,
        )

    # ------------------------------------------------------------ inference
    def predict(self, file_path: str) -> DetectionResult:
        if self._model is None:
            raise ModelUnavailableError(
                self._load_error or "Image model is not loaded."
            )

        started = time.perf_counter()

        batch = preprocess_file(
            file_path,
            input_size=self.input_size,
            mode=self.preprocess_mode,
        )

        raw = float(self._model.predict(batch, verbose=0)[0][0])

        p_positive = raw
        p_negative = 1.0 - raw

        if p_positive >= self.threshold:
            label, confidence = self.positive_label, p_positive
        else:
            label, confidence = self.negative_label, p_negative

        return DetectionResult(
            label=label,
            confidence=confidence,
            probabilities={
                self.positive_label: round(p_positive, 6),
                self.negative_label: round(p_negative, 6),
            },
            model_name=self._name,
            processing_time=time.perf_counter() - started,
            metadata={
                "raw_sigmoid": round(raw, 6),
                "threshold": self.threshold,
                "preprocess_mode": self.preprocess_mode,
                "input_size": self.input_size,
            },
        )

    def describe(self) -> dict:
        payload = super().describe()
        payload.update(
            {
                "weights_path": self.weights_path,
                "input_size": self.input_size,
                "preprocess_mode": self.preprocess_mode,
                "labels": [self.negative_label, self.positive_label],
                "threshold": self.threshold,
                "error": self._load_error,
            }
        )
        return payload
