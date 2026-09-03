"""
SHAP token attribution for the DistilBERT-based Text and Review detectors.

Both models are the same architecture (`distilbert-base-uncased` sequence
classifier) wired the same way (app/ml/text_detector.py,
app/ml/review_detector.py), so one implementation serves both — it only
touches the small public surface both classes expose
(`underlying_model`, `tokenizer`, `labels`, `device`, `max_length`), not
which modality the detector belongs to.

Approach: SHAP's `Explainer` with a `Text` masker treats the model as a
black box — it perturbs (masks out) tokens and observes how the predicted
probabilities move, then fits Shapley values explaining each token's
contribution to the predicted class. This is the standard modern
(`shap>=0.44`) text-explanation path and needs no gradient access, unlike
Grad-CAM, so it doesn't care that the underlying model is a plain
`transformers` model rather than anything Keras-specific.
"""
import numpy as np
import torch

from app.ml.text_preprocessing import load_text


def generate(detector, file_path: str) -> dict:
    """
    Run SHAP against a loaded TextDetector or ReviewDetector for the text
    file at `file_path`. Returns per-token attribution weights for
    whichever class the model actually predicted — not a fixed class index,
    since "Fake" is index 0 for Text but the two detectors don't
    necessarily share a label ordering (see each detector's own
    docstring on why labels are read from the checkpoint, not hardcoded).
    """
    import shap

    text = load_text(file_path)

    model = detector.underlying_model
    tokenizer = detector.tokenizer
    device = detector.device
    max_length = detector.max_length
    id2label = detector.labels

    def predict_proba(texts) -> np.ndarray:
        inputs = tokenizer(
            list(texts),
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)

        return probs.cpu().numpy()

    masker = shap.maskers.Text(tokenizer)
    explainer = shap.Explainer(predict_proba, masker, silent=True)
    shap_values = explainer([text])

    predicted_id = int(np.argmax(predict_proba([text])[0]))

    tokens = shap_values.data[0]
    weights = shap_values.values[0][:, predicted_id]

    attributions = [
        {"token": str(token), "weight": round(float(weight), 6)}
        for token, weight in zip(tokens, weights)
        # SHAP's Text masker emits whitespace/empty tokens as masking
        # boundaries — meaningless to show as an "important word" in the UI.
        if str(token).strip()
    ]

    return {
        "method": "shap",
        "artifact_type": "tokens",
        "artifact": attributions,
        "metadata": {
            "predicted_label": id2label.get(predicted_id, str(predicted_id)),
            "characters_read": len(text),
            "token_count": len(attributions),
        },
    }
