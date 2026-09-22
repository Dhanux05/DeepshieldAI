from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prediction import Prediction


class Explanation(Base):
    """
    A generated explainability artefact for one prediction.

    `method` is "gradcam", "shap", or "lime" (see xai/). `artifact_type`
    tells the frontend how to render `artifact`: "image" means `artifact` is
    a base64-encoded PNG (Grad-CAM's heatmap overlay, or LIME's superpixel
    boundary overlay for Image predictions); "tokens" means it's a JSON
    array of {token, weight} objects (SHAP's per-token attribution, or
    LIME's per-word attribution for Text/Review predictions) — same shape
    for both methods on purpose, so the frontend renders whichever one was
    generated identically. One row per (prediction, method) generated —
    generation is on-demand via POST /explanations/generate/{prediction_id},
    not automatic on every prediction, since none of the three methods are
    fast enough to run synchronously inline with inference.
    """

    __tablename__ = "explanations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id"),
        nullable=False,
        index=True,
    )

    method: Mapped[str] = mapped_column(String(20), nullable=False)

    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)

    artifact: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    prediction: Mapped["Prediction"] = relationship(
        "Prediction",
        back_populates="explanations",
    )
