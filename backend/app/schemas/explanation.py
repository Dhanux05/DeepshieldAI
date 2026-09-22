from datetime import datetime

from pydantic import BaseModel


class ExplanationResponse(BaseModel):
    """
    `artifact` is always a plain string on the wire: a base64-encoded PNG
    when `artifact_type == "image"` (Grad-CAM's heatmap, or LIME's
    superpixel-boundary overlay for Image predictions), or a JSON-encoded
    array of {token, weight} objects when `artifact_type == "tokens"`
    (SHAP's or LIME's per-token/per-word attribution for Text/Review
    predictions) — the frontend JSON.parses it in the second case rather
    than the API doing that unpacking, so the DB column, the schema, and the
    wire format all agree on "artifact is text" without a union type.
    """

    id: int
    prediction_id: int
    method: str
    artifact_type: str
    artifact: str
    model_name: str
    created_at: datetime

    class Config:
        from_attributes = True
