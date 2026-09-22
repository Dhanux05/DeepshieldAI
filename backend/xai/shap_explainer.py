"""
SHAP explanations for the DistilBERT-based Text/Review detectors, and for
the tabular XGBoost bot detector.

`generate()` handles Text and Review — both the same architecture
(`distilbert-base-uncased` sequence classifier) wired the same way
(app/ml/text_detector.py, app/ml/review_detector.py), so one implementation
serves both — it only touches the small public surface both classes expose
(`underlying_model`, `tokenizer`, `labels`, `device`, `max_length`), not
which modality the detector belongs to.

Approach: SHAP's `Explainer` with a `Text` masker treats the model as a
black box — it perturbs (masks out) tokens and observes how the predicted
probabilities move, then fits Shapley values explaining each token's
contribution to the predicted class. This is the standard modern
(`shap>=0.44`) text-explanation path and needs no gradient access, unlike
Grad-CAM, so it doesn't care that the underlying model is a plain
`transformers` model rather than anything Keras-specific.

`generate_tabular()` handles Account (the XGBoost bot detector). Tree
models get SHAP's exact, fast `TreeExplainer` instead of the black-box
text path — no perturbation sampling needed, since XGBoost's tree
structure lets SHAP compute exact Shapley values directly. The result is
returned in the SAME `artifact_type: "tokens"` shape as the text path
(feature name standing in for "token", SHAP value standing in for
"weight"), so the existing Explain.jsx renderer needs no changes at all
to show a bot-detection feature-importance bar chart.
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


def generate_tabular(detector, file_path: str) -> dict:
    """
    Run SHAP's TreeExplainer against the loaded BotDetector for the
    account-metadata JSON file at `file_path`.

    Re-runs the exact same `bot_preprocessing.extract_features` the
    detector itself used for the original prediction (same reasoning as
    `generate()` above: the explanation must reflect the same input the
    model actually scored). `datetime.now()` is called again here rather
    than reusing the original prediction's timestamp — a few seconds'
    drift in "account age" between predict and explain is immaterial
    (sub-millisecond effect on a days-scale feature), and avoiding a second
    plumbing path to pass timestamps through keeps this symmetric with how
    every other explainer in this file re-derives its input from the
    stored file rather than the original DetectionResult.
    """
    import json
    from datetime import datetime, timezone

    import shap

    from app.ml.bot_preprocessing import extract_features, features_to_vector

    with open(file_path, encoding="utf-8") as handle:
        account = json.load(handle)

    features = extract_features(
        account,
        reference_date=datetime.now(timezone.utc),
        account_age_fallback_days=getattr(detector, "_age_fallback_days", 0.0),
    )
    feature_names = detector.feature_order
    vector = [features_to_vector(features)]

    model = detector.underlying_model
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(vector)

    # Binary XGBClassifier: shap_values.values has shape (1, n_features) for
    # the "Bot" (class 1) log-odds contribution when the explainer is built
    # from an sklearn-wrapper booster; take row 0.
    values = shap_values.values[0]
    if values.ndim == 2:  # some shap/xgboost version combos add a class axis
        values = values[:, -1]

    bot_probability = float(model.predict_proba(vector)[0][1])
    predicted_bot = bot_probability >= 0.5

    # Flip sign when the predicted class is Human: `generate()` above always
    # reports each token's contribution TOWARD WHATEVER CLASS WAS ACTUALLY
    # PREDICTED (it indexes shap_values at `predicted_id`, not a fixed
    # class). TreeExplainer's raw output is always in "toward Bot" terms
    # regardless of the prediction, so without this flip a Human-predicted
    # account would show its supporting features as negative — the opposite
    # convention from every other explanation in the app, and confusing in
    # the UI ("why is the reason this is Human shown as a negative bar?").
    if not predicted_bot:
        values = -values

    attributions = [
        {"token": name, "weight": round(float(weight), 6)}
        for name, weight in zip(feature_names, values)
    ]
    attributions.sort(key=lambda item: abs(item["weight"]), reverse=True)

    return {
        "method": "shap",
        "artifact_type": "tokens",
        "artifact": attributions,
        "metadata": {
            "predicted_label": "Bot" if predicted_bot else "Human",
            "feature_count": len(attributions),
        },
    }
