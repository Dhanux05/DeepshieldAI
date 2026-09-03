from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ModelUnavailableError(RuntimeError):
    """
    Raised when a detector cannot serve a request because its weights are
    missing, its framework is not installed, or it failed to load at startup.

    Distinct from a generic failure on purpose: the API maps this to 503
    (the service is fine, this capability is not) rather than 500.
    """


@dataclass(frozen=True)
class DetectionResult:
    """Immutable inference output — the only type `ml/` returns to `app/`."""

    label: str
    confidence: float
    probabilities: dict[str, float]
    model_name: str
    processing_time: float
    metadata: dict = field(default_factory=dict)


class BaseDetector(ABC):
    """
    Contract every modality detector honours.

    Defining this now means the audio, text and review models drop in as new
    subclasses rather than as a rewrite of the service layer.
    """

    #: Document type this detector handles ("Image", "Audio", "Text", ...)
    modality: str = "Unknown"

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier persisted on the Prediction row."""

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """True once weights are loaded and `predict` can be called."""

    @abstractmethod
    def load(self) -> None:
        """Load weights into memory. Called once, at application startup."""

    @abstractmethod
    def predict(self, file_path: str) -> DetectionResult:
        """Run inference on one file."""

    def describe(self) -> dict:
        """Status payload surfaced by the /predictions/models endpoint."""
        return {
            "modality": self.modality,
            "model_name": self.model_name,
            "ready": self.is_ready,
        }
