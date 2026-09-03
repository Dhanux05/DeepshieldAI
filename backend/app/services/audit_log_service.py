from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.audit_log import (
    AuditLogCreate,
    AuditLogUpdate,
)


class AuditLogService:

    def __init__(
        self,
        audit_repository: AuditLogRepository,
        user_repository: UserRepository,
    ):
        self.audit_repository = audit_repository
        self.user_repository = user_repository

    def create_audit_log(
        self,
        audit_data: AuditLogCreate,
    ):

        user = self.user_repository.get_user_by_id(
            audit_data.user_id
        )

        if user is None:
            raise ValueError("User not found.")

        audit_log = AuditLog(
            user_id=audit_data.user_id,
            action=audit_data.action,
            resource=audit_data.resource,
            details=audit_data.details,
            ip_address=audit_data.ip_address,
        )

        return self.audit_repository.create_audit_log(
            audit_log
        )

    def get_audit_log_by_id(
        self,
        audit_log_id: int,
    ):

        audit_log = (
            self.audit_repository.get_audit_log_by_id(
                audit_log_id
            )
        )

        if audit_log is None:
            raise ValueError(
                "Audit log not found."
            )

        return audit_log

    def get_all_audit_logs(self, skip: int = 0, limit: int = 50):

        return self.audit_repository.get_all_audit_logs(skip, limit)

    def get_logs_by_user(
        self,
        user_id: int,
    ):

        return self.audit_repository.get_logs_by_user(
            user_id
        )

    def update_audit_log(
        self,
        audit_log_id: int,
        updated_data: AuditLogUpdate,
    ):

        audit_log = (
            self.audit_repository.get_audit_log_by_id(
                audit_log_id
            )
        )

        if audit_log is None:
            raise ValueError(
                "Audit log not found."
            )

        if updated_data.action is not None:
            audit_log.action = updated_data.action

        if updated_data.resource is not None:
            audit_log.resource = updated_data.resource

        if updated_data.details is not None:
            audit_log.details = updated_data.details

        if updated_data.ip_address is not None:
            audit_log.ip_address = updated_data.ip_address

        return self.audit_repository.update_audit_log(
            audit_log
        )

    def delete_audit_log(
        self,
        audit_log_id: int,
    ):

        audit_log = (
            self.audit_repository.get_audit_log_by_id(
                audit_log_id
            )
        )

        if audit_log is None:
            raise ValueError(
                "Audit log not found."
            )

        self.audit_repository.delete_audit_log(
            audit_log
        )

        return {
            "message": "Audit log deleted successfully."
        }