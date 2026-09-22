"""
XGBoost account-metadata classifier: is this Twitter-style account a bot
or a human?

Unlike Image/Audio/Video/Text/Review, the input here isn't a media file —
it's structured account metadata (follower/following counts, account age,
bio text, etc.), packaged by the frontend as a small JSON upload. See
document_service.py's `document_type` override for how a `.json` upload
gets routed here instead of to TextDetector (which normally owns .json).

Trained by scripts/train_bot_detector.py on `training_data_2_csv_UTF.csv`
(2,797 labelled accounts; see that script's docstring for provenance and
the real held-out test metrics in models/bot/training_report.md).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger
from app.ml.base import BaseDetector, DetectionResult, ModelUnavailableError
from app.ml.bot_preprocessing import FEATURE_ORDER, extract_features, features_to_vector

logger = get_logger(__name__)


class BotDetector(BaseDetector):
    """
    Loads `bot_xgb_model.json` + `feature_schema.json` (both written by
    scripts/train_bot_detector.py) at startup. `feature_schema.json` is not
    optional metadata — it carries `account_age_fallback_days`, the
    training-set median age used when a live upload's `created_at` can't be
    parsed, so serving degrades exactly the way training was evaluated to
    degrade, rather than guessing a different fallback.
    """

    modality = "Account"

    def __init__(
        self,
        model_path: str,
        feature_schema_path: str,
        decision_threshold: float | None = None,
    ):
        self.model_path = model_path
        self.feature_schema_path = feature_schema_path
        self._override_threshold = decision_threshold

        self._model = None
        self._label_names: dict[int, str] = {0: "Human", 1: "Bot"}
        self._decision_threshold = 0.5
        self._age_fallback_days = 0.0
        self._name = "xgboost_deepshield_bot"
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
        """Read-only access for xai/shap_explainer.py's tabular SHAP path."""
        return self._model

    @property
    def feature_order(self) -> list[str]:
        """Read-only access for xai/shap_explainer.py — feature names for the SHAP artifact."""
        return FEATURE_ORDER

    def load(self) -> None:
        """Load the trained model + its feature schema once, at startup."""
        model_path = Path(self.model_path)
        schema_path = Path(self.feature_schema_path)

        if not model_path.exists() or not schema_path.exists():
            self._load_error = (
                f"Bot model artefacts not found (expected {model_path} and "
                f"{schema_path}). Run scripts/train_bot_detector.py first."
            )
            logger.warning("BotDetector: %s", self._load_error)
            return

        try:
            import xgboost as xgb
        except ImportError:
            self._load_error = (
                "xgboost is not installed. Install requirements/ml.txt to "
                "enable bot-account inference."
            )
            logger.warning("BotDetector: %s", self._load_error)
            return

        try:
            model = xgb.XGBClassifier()
            model.load_model(str(model_path))

            schema = json.loads(schema_path.read_text())
        except Exception as exc:  # noqa: BLE001 - surfaced via /models
            self._load_error = f"{type(exc).__name__}: {exc}"
            logger.exception("BotDetector failed to load %s", model_path)
            return

        if schema.get("feature_order") != FEATURE_ORDER:
            self._load_error = (
                "feature_schema.json's feature_order does not match the "
                "current bot_preprocessing.FEATURE_ORDER. The model was "
                "trained against a different feature set — retrain before "
                "serving to avoid silently misaligned predictions."
            )
            logger.error("BotDetector: %s", self._load_error)
            return

        self._model = model
        self._label_names = {
            int(idx): label for idx, label in schema.get("label_names", {0: "Human", 1: "Bot"}).items()
        }
        self._age_fallback_days = float(schema.get("account_age_fallback_days", 0.0))
        self._decision_threshold = (
            self._override_threshold
            if self._override_threshold is not None
            else float(schema.get("decision_threshold", 0.5))
        )

        logger.info(
            "BotDetector ready — %s (features=%d, threshold=%.2f, test_f1=%s)",
            self._name,
            len(FEATURE_ORDER),
            self._decision_threshold,
            schema.get("test_metrics", {}).get("f1"),
        )

    # ------------------------------------------------------------ inference
    def predict(self, file_path: str) -> DetectionResult:
        if self._model is None:
            raise ModelUnavailableError(self._load_error or "Bot model is not loaded.")

        started = time.perf_counter()

        with open(file_path, encoding="utf-8") as handle:
            account = json.load(handle)

        if not isinstance(account, dict):
            raise ValueError(
                "Account upload must be a single JSON object with account "
                "fields (followers_count, friends_count, created_at, ...)."
            )

        features = extract_features(
            account,
            reference_date=datetime.now(timezone.utc),
            account_age_fallback_days=self._age_fallback_days,
        )
        vector = [features_to_vector(features)]

        bot_probability = float(self._model.predict_proba(vector)[0][1])
        predicted_id = 1 if bot_probability >= self._decision_threshold else 0
        label = self._label_names.get(predicted_id, str(predicted_id))

        probabilities = {
            self._label_names.get(0, "Human"): round(1.0 - bot_probability, 6),
            self._label_names.get(1, "Bot"): round(bot_probability, 6),
        }

        return DetectionResult(
            label=label,
            confidence=bot_probability if predicted_id == 1 else 1.0 - bot_probability,
            probabilities=probabilities,
            model_name=self._name,
            processing_time=time.perf_counter() - started,
            metadata={
                "decision_threshold": self._decision_threshold,
                "account_age_days": round(features["account_age_days"], 1),
                "screen_name": account.get("screen_name"),
            },
        )

    def describe(self) -> dict:
        payload = super().describe()
        payload.update(
            {
                "model_path": self.model_path,
                "feature_count": len(FEATURE_ORDER),
                "labels": list(self._label_names.values()) or None,
                "error": self._load_error,
            }
        )
        return payload
