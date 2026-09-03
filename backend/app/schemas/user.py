from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """
    Self-service profile edit.

    Deliberately omits `role_id` and `is_active` — a user must never be able
    to escalate their own privileges or reactivate a disabled account by
    POSTing extra fields. Those live behind admin-only endpoints (phase 11).
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserMeResponse(BaseModel):
    """
    The authenticated user's own profile.

    Differs from UserResponse by resolving `role_id` into a human-readable
    `role_name`. The frontend needs the name (not the id) to render the role
    badge and to hide admin-only navigation, and it should never have to
    hardcode an id->name mapping of its own.
    """

    id: int
    full_name: str
    email: EmailStr
    role_id: int
    role_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
