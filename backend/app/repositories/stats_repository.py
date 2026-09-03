from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.knowledge_base import KnowledgeBase
from app.models.prediction import Prediction
from app.models.report import Report


class StatsRepository:
    """
    Read-only aggregate queries for the dashboard.

    Deliberately separate from PredictionRepository: that class owns the
    lifecycle of a single entity, whereas this one spans several tables and
    only ever reads. Mixing the two would make PredictionRepository depend on
    Document, Report and KnowledgeBase for no good reason.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- totals
    def count_predictions(self) -> int:
        return self.db.query(func.count(Prediction.id)).scalar() or 0

    def count_documents(self) -> int:
        return self.db.query(func.count(Document.id)).scalar() or 0

    def count_reports(self) -> int:
        return self.db.query(func.count(Report.id)).scalar() or 0

    def count_knowledge_entries(self) -> int:
        return self.db.query(func.count(KnowledgeBase.id)).scalar() or 0

    # ------------------------------------------------------------ averages
    def average_confidence(self) -> float | None:
        value = self.db.query(func.avg(Prediction.confidence_score)).scalar()
        return float(value) if value is not None else None

    def average_processing_time(self) -> float | None:
        value = self.db.query(func.avg(Prediction.processing_time)).scalar()
        return float(value) if value is not None else None

    # ---------------------------------------------------------- breakdowns
    def _grouped_count(self, column) -> list[tuple[str, int]]:
        """GROUP BY <column> ORDER BY count DESC — the shape every card wants."""
        rows = (
            self.db.query(column, func.count().label("count"))
            .group_by(column)
            .order_by(func.count().desc())
            .all()
        )
        return [(str(name), int(count)) for name, count in rows]

    def label_breakdown(self) -> list[tuple[str, int]]:
        return self._grouped_count(Prediction.predicted_label)

    def status_breakdown(self) -> list[tuple[str, int]]:
        return self._grouped_count(Prediction.processing_status)

    def model_breakdown(self) -> list[tuple[str, int]]:
        return self._grouped_count(Prediction.model_name)

    def document_type_breakdown(self) -> list[tuple[str, int]]:
        rows = (
            self.db.query(
                DocumentType.type_name,
                func.count(Document.id).label("count"),
            )
            .join(Document, Document.document_type_id == DocumentType.id)
            .group_by(DocumentType.type_name)
            .order_by(func.count(Document.id).desc())
            .all()
        )
        return [(str(name), int(count)) for name, count in rows]

    # ------------------------------------------------------------ time series
    def daily_counts(self, days: int = 14) -> list[tuple[str, int]]:
        """
        Predictions per calendar day over the trailing window.

        `func.date(...)` is used rather than a Postgres-only `date_trunc` so
        the same query runs under SQLite in the test suite (Phase 12).
        """
        since = datetime.now(UTC) - timedelta(days=days)
        day = func.date(Prediction.created_at)

        rows = (
            self.db.query(day.label("day"), func.count().label("count"))
            .filter(Prediction.created_at >= since)
            .group_by(day)
            .order_by(day)
            .all()
        )
        return [(str(value), int(count)) for value, count in rows]
