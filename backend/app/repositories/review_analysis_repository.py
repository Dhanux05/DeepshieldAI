from sqlalchemy.orm import Session

from app.models.review_analysis import ReviewAnalysis


class ReviewAnalysisRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_review_analysis(
        self,
        review: ReviewAnalysis,
    ) -> ReviewAnalysis:

        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        return review

    def get_review_analysis_by_id(
        self,
        review_id: int,
    ) -> ReviewAnalysis | None:

        return (
            self.db.query(ReviewAnalysis)
            .filter(ReviewAnalysis.id == review_id)
            .first()
        )

    def get_all_review_analyses(self, skip: int = 0, limit: int = 50):

        return (
            self.db.query(ReviewAnalysis)
            .order_by(
                ReviewAnalysis.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_prediction(
        self,
        prediction_id: int,
    ):

        return (
            self.db.query(ReviewAnalysis)
            .filter(
                ReviewAnalysis.prediction_id == prediction_id
            )
            .order_by(
                ReviewAnalysis.created_at.desc()
            )
            .all()
        )

    def update_review_analysis(
        self,
        review: ReviewAnalysis,
    ) -> ReviewAnalysis:

        self.db.commit()
        self.db.refresh(review)

        return review

    def delete_review_analysis(
        self,
        review: ReviewAnalysis,
    ):

        self.db.delete(review)
        self.db.commit()