from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(
        self,
        audit_log: AuditLog
    ) -> AuditLog:

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def get_audit_log_by_id(
        self,
        audit_log_id: int
    ) -> AuditLog | None:

        return (
            self.db.query(AuditLog)
            .filter(AuditLog.id == audit_log_id)
            .first()
        )

    def get_all_audit_logs(self, skip: int = 0, limit: int = 50):

        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_logs_by_user(
        self,
        user_id: int
    ):

        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .all()
        )

    def update_audit_log(
        self,
        audit_log: AuditLog
    ) -> AuditLog:

        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def delete_audit_log(
        self,
        audit_log: AuditLog
    ) -> None:

        self.db.delete(audit_log)
        self.db.commit()