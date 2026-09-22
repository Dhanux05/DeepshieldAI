import json

from app.core.logging import get_logger
from app.ml.base import ModelUnavailableError
from app.ml.registry import registry
from app.models.explanation import Explanation
from app.repositories.explanation_repository import ExplanationRepository
from app.repositories.prediction_repository import PredictionRepository
from xai import gradcam, lime_explainer, shap_explainer

logger = get_logger(__name__)

#: Which explanation methods are meaningful for which modality. Grad-CAM
#: needs a convolutional feature map (Image only); SHAP covers the two
#: DistilBERT-based modalities via its black-box text path, AND Account via
#: its exact TreeExplainer path for XGBoost (see xai/shap_explainer.py —
#: `generate()` vs `generate_tabular()`). LIME is the odd one out — it's
#: model-agnostic, so it applies to Image (superpixel perturbation,
#: validating Grad-CAM without touching gradients) AND to Text/Review (token
#: perturbation, a second attribution to set beside SHAP's). Audio and Video
#: remain out of scope — attempting either raises a clear 400 rather than a
#: confusing failure deep inside an xai module.
SUPPORTED_METHODS: dict[str, set[str]] = {
    "gradcam": {"Image"},
    "shap": {"Text", "Review", "Account"},
    "lime": {"Image", "Text", "Review"},
}


class ExplanationService:

    def __init__(
        self,
        repository: ExplanationRepository,
        prediction_repository: PredictionRepository,
    ):
        self.repository = repository
        self.prediction_repository = prediction_repository

    def generate_explanation(
        self,
        prediction_id: int,
        method: str,
    ) -> Explanation:

        if method not in SUPPORTED_METHODS:
            raise ValueError(
                f"Unknown explanation method '{method}'. "
                f"Available: {', '.join(SUPPORTED_METHODS)}."
            )

        prediction = self.prediction_repository.get_prediction_by_id(
            prediction_id
        )

        if prediction is None:
            raise ValueError("Prediction not found.")

        document = prediction.document
        modality = document.document_type.type_name

        if modality not in SUPPORTED_METHODS[method]:
            raise ValueError(
                f"'{method}' is not available for {modality} predictions. "
                f"It currently supports: {', '.join(SUPPORTED_METHODS[method])}."
            )

        detector = registry.get_detector(modality)

        if method == "gradcam":
            result = gradcam.generate(
                model=detector.underlying_model,
                file_path=document.file_path,
                input_size=detector.input_size,
                preprocess_mode=detector.preprocess_mode,
            )
            artifact = result["artifact"]

        elif method == "shap":
            if modality == "Account":
                result = shap_explainer.generate_tabular(
                    detector=detector,
                    file_path=document.file_path,
                )
            else:  # "Text" or "Review"
                result = shap_explainer.generate(
                    detector=detector,
                    file_path=document.file_path,
                )
            # Stored (and shipped over the wire) as a JSON string — see
            # ExplanationResponse's docstring for why.
            artifact = json.dumps(result["artifact"])

        else:  # "lime" — the one method that branches on modality itself,
            # since it has a genuinely different xai/ entry point (and
            # artifact_type) for Image vs. Text/Review.
            if modality == "Image":
                result = lime_explainer.generate_image(
                    model=detector.underlying_model,
                    file_path=document.file_path,
                    input_size=detector.input_size,
                    preprocess_mode=detector.preprocess_mode,
                    positive_label=detector.positive_label,
                    negative_label=detector.negative_label,
                    threshold=detector.threshold,
                )
                artifact = result["artifact"]
            else:  # "Text" or "Review"
                result = lime_explainer.generate_text(
                    detector=detector,
                    file_path=document.file_path,
                )
                artifact = json.dumps(result["artifact"])

        explanation = Explanation(
            prediction_id=prediction_id,
            method=result["method"],
            artifact_type=result["artifact_type"],
            artifact=artifact,
            model_name=detector.model_name,
        )

        logger.info(
            "Explanation generated — prediction=%s method=%s modality=%s",
            prediction_id,
            method,
            modality,
        )

        return self.repository.create_explanation(explanation)

    def get_by_prediction(
        self,
        prediction_id: int,
    ):
        return self.repository.get_by_prediction(prediction_id)

    def get_explanation_by_id(
        self,
        explanation_id: int,
    ):
        explanation = self.repository.get_explanation_by_id(explanation_id)

        if explanation is None:
            raise ValueError("Explanation not found.")

        return explanation
