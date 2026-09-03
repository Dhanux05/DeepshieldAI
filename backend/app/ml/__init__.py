"""
Machine-learning inference layer.

This package knows nothing about FastAPI, SQLAlchemy or HTTP. It takes a file
path and returns a `DetectionResult` dataclass. That boundary is what lets the
detectors be unit-tested without a database and reused unchanged inside a
training notebook or a Celery worker.
"""

from app.ml.base import BaseDetector, DetectionResult, ModelUnavailableError

__all__ = ["BaseDetector", "DetectionResult", "ModelUnavailableError"]
