from sqlalchemy.orm import Session

from app.models.report import Report


class ReportRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_report(
        self,
        report: Report
    ) -> Report:

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return report

    def get_report_by_id(
        self,
        report_id: int
    ) -> Report | None:

        return (
            self.db.query(Report)
            .filter(Report.id == report_id)
            .first()
        )

    def get_reports_by_prediction(
        self,
        prediction_id: int
    ):

        return (
            self.db.query(Report)
            .filter(
                Report.prediction_id == prediction_id
            )
            .order_by(Report.created_at.desc())
            .all()
        )

    def get_all_reports(self, skip: int = 0, limit: int = 50):

        return (
            self.db.query(Report)
            .order_by(Report.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_report(
        self,
        report: Report
    ) -> Report:

        self.db.commit()
        self.db.refresh(report)

        return report

    def delete_report(
        self,
        report: Report
    ) -> None:

        self.db.delete(report)
        self.db.commit()