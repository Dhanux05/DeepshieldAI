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

    `method` is "gradcam" or "shap" (Phase 7 scope — see xai/). `artifact_type`
    tells the frontend how to render `artifact`: "image" means `artifact` is
    a base64-encoded PNG (Grad-CAM's heatmap overlay); "tokens" means it's a
    JSON array of {token, weight} objects (SHAP's per-token attribution).
    One row per (prediction, method) generated — generation is on-demand via
    POST /explanations/generate/{prediction_id}, not automatic on every
    prediction, since both methods are too slow to run synchronously inline
    with inference (see PROJECT_STATUS_RECHECK's note on Phase 8/async).
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
