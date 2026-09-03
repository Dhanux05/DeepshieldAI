from datetime import UTC, date, datetime, timedelta

from app.repositories.stats_repository import StatsRepository
from app.schemas.prediction import CountItem, DailyCount, PredictionStats


class StatsService:
    """Assembles the dashboard payload from the aggregate repository."""

    def __init__(self, repository: StatsRepository):
        self.repository = repository

    @staticmethod
    def _to_items(rows: list[tuple[str, int]]) -> list[CountItem]:
        return [CountItem(name=name, count=count) for name, count in rows]

    @staticmethod
    def _fill_missing_days(
        rows: list[tuple[str, int]],
        days: int,
    ) -> list[DailyCount]:
        """
        Produce one entry per day in the window, including days with no
        activity.

        Without this the frontend chart would silently compress gaps — three
        predictions on Monday and three on Friday would render as two adjacent
        points, implying continuous activity that never happened.
        """
        counts = {str(day): count for day, count in rows}
        today = datetime.now(UTC).date()

        series: list[DailyCount] = []
        for offset in range(days - 1, -1, -1):
            current: date = today - timedelta(days=offset)
            series.append(
                DailyCount(
                    day=current,
                    count=counts.get(current.isoformat(), 0),
                )
            )
        return series

    def get_dashboard_stats(self, days: int = 14) -> PredictionStats:
        repo = self.repository

        return PredictionStats(
            total_predictions=repo.count_predictions(),
            total_documents=repo.count_documents(),
            total_reports=repo.count_reports(),
            total_knowledge_entries=repo.count_knowledge_entries(),
            average_confidence=repo.average_confidence(),
            average_processing_time=repo.average_processing_time(),
            label_breakdown=self._to_items(repo.label_breakdown()),
            status_breakdown=self._to_items(repo.status_breakdown()),
            model_breakdown=self._to_items(repo.model_breakdown()),
            document_type_breakdown=self._to_items(
                repo.document_type_breakdown()
            ),
            daily_counts=self._fill_missing_days(
                repo.daily_counts(days),
                days,
            ),
        )
