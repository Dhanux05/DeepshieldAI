from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.bot_analysis import BotAnalysis
    from app.models.document import Document
    from app.models.explanation import Explanation
    from app.models.report import Report
    from app.models.review_analysis import ReviewAnalysis


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    predicted_label: Mapped[str] = mapped_column(String(50), nullable=False)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    processing_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Pending",
    )

    processing_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ------------------------------------------------------- relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="predictions",
    )

    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    bot_analyses: Mapped[list["BotAnalysis"]] = relationship(
        "BotAnalysis",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    review_analyses: Mapped[list["ReviewAnalysis"]] = relationship(
        "ReviewAnalysis",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    explanations: Mapped[list["Explanation"]] = relationship(
        "Explanation",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, label='{self.predicted_label}', "
            f"confidence={self.confidence_score:.3f})>"
        )
