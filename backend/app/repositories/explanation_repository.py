from sqlalchemy.orm import Session

from app.models.explanation import Explanation


class ExplanationRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_explanation(
        self,
        explanation: Explanation,
    ) -> Explanation:

        self.db.add(explanation)
        self.db.commit()
        self.db.refresh(explanation)

        return explanation

    def get_explanation_by_id(
        self,
        explanation_id: int,
    ) -> Explanation | None:

        return (
            self.db.query(Explanation)
            .filter(Explanation.id == explanation_id)
            .first()
        )

    def get_by_prediction(
        self,
        prediction_id: int,
    ):

        return (
            self.db.query(Explanation)
            .filter(
                Explanation.prediction_id == prediction_id
            )
            .order_by(Explanation.created_at.desc())
            .all()
        )
