from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_active_user
from app.models.user import User


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    """
    Dependency factory returning a guard that admits only the named roles.

    Usage:
        @router.delete(
            "/{prediction_id}",
            dependencies=[Depends(require_roles(Roles.ADMIN, Roles.ANALYST))],
        )

    Why a factory? FastAPI dependencies cannot take arbitrary arguments at the
    call site, so we build a closure that captures the allowed role names and
    return the actual dependency function.
    """

    def guard(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        role_name = current_user.role.role_name if current_user.role else None

        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Insufficient permissions. "
                    f"Requires one of: {', '.join(allowed_roles)}."
                ),
            )

        return current_user

    return guard
