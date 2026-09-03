from sqlalchemy.orm import Session

from app.models.bot_analysis import BotAnalysis


class BotAnalysisRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_bot_analysis(
        self,
        analysis: BotAnalysis,
    ) -> BotAnalysis:

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def get_bot_analysis_by_id(
        self,
        analysis_id: int,
    ) -> BotAnalysis | None:

        return (
            self.db.query(BotAnalysis)
            .filter(BotAnalysis.id == analysis_id)
            .first()
        )

    def get_all_bot_analyses(self, skip: int = 0, limit: int = 50):

        return (
            self.db.query(BotAnalysis)
            .order_by(BotAnalysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_prediction(
        self,
        prediction_id: int,
    ):

        return (
            self.db.query(BotAnalysis)
            .filter(
                BotAnalysis.prediction_id == prediction_id
            )
            .order_by(BotAnalysis.created_at.desc())
            .all()
        )

    def update_bot_analysis(
        self,
        analysis: BotAnalysis,
    ) -> BotAnalysis:

        self.db.commit()
        self.db.refresh(analysis)

        return analysis

    def delete_bot_analysis(
        self,
        analysis: BotAnalysis,
    ):

        self.db.delete(analysis)
        self.db.commit()