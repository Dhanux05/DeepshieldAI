"""
LIME (Local Interpretable Model-Agnostic Explanations) for two of this
project's three explained modalities.

Unlike Grad-CAM (needs gradient access to a specific conv layer) and SHAP
(needs a masker built for its specific input type), LIME treats the
classifier as a pure black box: it perturbs the input many times, asks the
model to score each perturbation, and fits a small interpretable model
(weighted linear regression) around just that one prediction. That
generality is exactly why it earns a place alongside Grad-CAM/SHAP rather
than replacing them — for Text/Review it gives a second, independently
computed attribution to set beside SHAP's Shapley values (do the two
methods agree on which words mattered?), and for Image it validates
Grad-CAM's gradient-based heatmap with a method that never looks at the
model's internals at all.

Two entry points, one per LIME sub-module:
    generate_text(detector, file_path)    -> lime.lime_text  (Text/Review)
    generate_image(model, file_path, ...) -> lime.lime_image (Image)
"""
import base64
import io

import numpy as np
import torch
from PIL import Image

from app.ml.preprocessing import load_image
from app.ml.text_preprocessing import load_text

#: LIME's own defaults (num_samples=5000 for text, 1000 for images) assume a
#: throwaway research script, not a synchronous HTTP request someone is
#: waiting on. Both underlying models here are small enough (DistilBERT-base,
#: MobileNetV2) that these lower sample counts still converge to a stable
#: explanation in a few seconds on CPU rather than upwards of a minute.
TEXT_NUM_SAMPLES = 300
TEXT_NUM_FEATURES = 12
TEXT_BATCH_SIZE = 16

IMAGE_NUM_SAMPLES = 300
IMAGE_NUM_FEATURES = 8
IMAGE_BATCH_SIZE = 20


def generate_text(detector, file_path: str) -> dict:
    """
    Run LIME against a loaded TextDetector or ReviewDetector for the text
    file at `file_path`.

    `detector` needs the same small public surface SHAP already relies on
    (`underlying_model`, `tokenizer`, `device`, `max_length`, `labels`) — see
    xai/shap_explainer.py's docstring for why one implementation can serve
    both DistilBERT-based detectors interchangeably.
    """
    from lime.lime_text import LimeTextExplainer

    text = load_text(file_path)

    model = detector.underlying_model
    tokenizer = detector.tokenizer
    device = detector.device
    max_length = detector.max_length
    id2label = detector.labels
    class_names = [id2label[i] for i in sorted(id2label)]

    def predict_proba(texts) -> np.ndarray:
        """
        Same contract as SHAP's predict_proba (xai/shap_explainer.py): a
        list of strings in, an (N, num_classes) probability matrix out.
        LIME calls this exactly once per explain_instance(), with the full
        perturbed-sample list in one go — chunked here rather than
        tokenised in a single shot, so a num_samples=300 call builds
        TEXT_BATCH_SIZE-row tensors instead of one 300-row tensor, which is
        the kind of thing that quietly triples memory use on a laptop for
        no accuracy benefit over doing it in slices.
        """
        texts = list(texts)
        if not texts:
            # Defensive only — LIME always calls this with either the single
            # query text or a full num_samples batch, never an empty list —
            # but np.concatenate([]) below would raise ValueError if it ever
            # did, and an empty (0, num_classes) result is the correct
            # answer for "zero inputs" either way.
            return np.empty((0, len(id2label)))

        all_probs = []

        for start in range(0, len(texts), TEXT_BATCH_SIZE):
            batch = texts[start : start + TEXT_BATCH_SIZE]
            inputs = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length,
            )
            inputs = {key: value.to(device) for key, value in inputs.items()}

            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)

            all_probs.append(probs.cpu().numpy())

        return np.concatenate(all_probs, axis=0)

    predicted_id = int(np.argmax(predict_proba([text])[0]))

    explainer = LimeTextExplainer(class_names=class_names)
    explanation = explainer.explain_instance(
        text,
        predict_proba,
        labels=(predicted_id,),
        num_features=TEXT_NUM_FEATURES,
        num_samples=TEXT_NUM_SAMPLES,
    )

    attributions = [
        {"token": str(word), "weight": round(float(weight), 6)}
        for word, weight in explanation.as_list(label=predicted_id)
    ]

    return {
        "method": "lime",
        "artifact_type": "tokens",
        "artifact": attributions,
        "metadata": {
            "predicted_label": id2label.get(predicted_id, str(predicted_id)),
            "characters_read": len(text),
            "token_count": len(attributions),
            "num_samples": TEXT_NUM_SAMPLES,
        },
    }


def _scale_batch(batch: np.ndarray, mode: str) -> np.ndarray:
    """
    Mirrors app/ml/preprocessing.to_batch's scaling branches exactly. LIME
    hands classifier_fn perturbed copies of the raw uint8 image, which still
    need the same pixel scaling the detector was trained and served with
    before they reach the model — see preprocessing.py's module docstring on
    why guessing this wrong produces confident nonsense, not an error.
    """
    array = batch.astype("float32")
    if mode == "mobilenet_v2":
        return array / 127.5 - 1.0
    if mode == "rescale":
        return array / 255.0
    return array  # "raw" — untouched


def generate_image(
    model,
    file_path: str,
    input_size: int = 224,
    preprocess_mode: str = "rescale",
    positive_label: str = "Deepfake",
    negative_label: str = "Genuine",
    threshold: float = 0.5,
) -> dict:
    """
    Run LIME against a loaded ImageDetector's Keras model for the image at
    `file_path`.

    `model`/`input_size`/`preprocess_mode`/`positive_label`/`negative_label`/
    `threshold` are the same ImageDetector attributes xai/gradcam.py takes,
    so this explanation sees exactly what the classifier saw and targets the
    same predicted class the user was shown — not a fresh argmax that could
    disagree with ImageDetector's own (configurable) decision threshold.
    """
    from lime.lime_image import LimeImageExplainer
    from skimage.segmentation import mark_boundaries

    original = load_image(file_path)
    resized = original.resize((input_size, input_size), Image.BILINEAR)
    image_array = np.asarray(resized, dtype="uint8")

    def classifier_fn(images: np.ndarray) -> np.ndarray:
        """
        LIME's black-box contract: a batch of perturbed uint8 images in, an
        (N, 2) probability matrix out — column 0 is P(negative_label),
        column 1 is P(positive_label), matching class_names ordering below.
        """
        batch = _scale_batch(images, preprocess_mode)
        raw = np.asarray(model.predict(batch, verbose=0)).reshape(-1)
        return np.stack([1.0 - raw, raw], axis=1)

    baseline_probs = classifier_fn(np.expand_dims(image_array, axis=0))[0]
    predicted_index = 1 if baseline_probs[1] >= threshold else 0
    predicted_label = [negative_label, positive_label][predicted_index]

    explainer = LimeImageExplainer()
    explanation = explainer.explain_instance(
        image_array,
        classifier_fn,
        labels=(predicted_index,),
        top_labels=None,  # explicit: explain the predicted class only
        hide_color=0,
        num_samples=IMAGE_NUM_SAMPLES,
        batch_size=IMAGE_BATCH_SIZE,
    )

    temp, mask = explanation.get_image_and_mask(
        label=predicted_index,
        positive_only=True,
        num_features=IMAGE_NUM_FEATURES,
        hide_rest=False,
    )

    boundary_image = mark_boundaries(temp.astype("float64") / 255.0, mask)
    overlay = Image.fromarray(np.uint8(np.clip(boundary_image, 0, 1) * 255))

    buffer = io.BytesIO()
    overlay.save(buffer, format="PNG")
    artifact = base64.b64encode(buffer.getvalue()).decode("ascii")

    return {
        "method": "lime",
        "artifact_type": "image",
        "artifact": artifact,
        "metadata": {
            "predicted_label": predicted_label,
            "input_size": input_size,
            "num_samples": IMAGE_NUM_SAMPLES,
            "num_features": IMAGE_NUM_FEATURES,
        },
    }
