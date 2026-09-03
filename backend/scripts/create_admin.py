"""
Create or promote an administrator account.

There is deliberately no default admin with a well-known password — a
hardcoded `admin/admin` is the single most common way a student project gets
marked down on security, and it would ship straight into any deployment.

Usage (from the `backend/` directory):

    python -m scripts.create_admin --email you@example.com --name "Your Name"

You will be prompted for the password (it is never passed on the command
line, where it would land in your shell history).

If the email already exists, the account is promoted to Admin instead.
"""

import argparse
import getpass
import sys

from sqlalchemy.orm import Session

from app.constants.roles import Roles
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User

MIN_PASSWORD_LENGTH = 8


def get_admin_role(db: Session) -> Role:
    role = db.query(Role).filter(Role.role_name == Roles.ADMIN).first()

    if role is None:
        raise SystemExit(
            "The 'Admin' role does not exist. Run `python -m scripts.seed_roles` first."
        )

    return role


def prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        raise SystemExit("Passwords do not match.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    return password


def create_admin(
    db: Session,
    email: str,
    full_name: str,
    password: str | None = None,
) -> None:
    role = get_admin_role(db)

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        # Capture this BEFORE mutating the row, otherwise the comparison is
        # always true and the script can never report a promotion.
        was_admin = existing.role_id == role.id

        # Reset the password too when one was supplied, so re-running the
        # command is a reliable way to regain access to a locked-out account.
        if password:
            existing.password_hash = hash_password(password)

        existing.role_id = role.id
        existing.is_active = True
        db.commit()

        if was_admin:
            action = "Updated password for existing Admin"
        else:
            action = "Promoted existing user to Admin:"

        print(f"{action} '{email}'.")
        return

    if password is None:
        password = prompt_password()
    elif len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role_id=role.id,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"Created Admin account '{email}' (id={user.id}).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or promote a DeepShieldAI administrator."
    )
    parser.add_argument("--email", required=True, help="Account email address.")
    parser.add_argument(
        "--name",
        default="Administrator",
        help="Full name for a newly created account.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help=(
            "Password, for non-interactive/demo use. Omit this to be prompted "
            "securely instead — anything passed here is visible in your shell "
            "history and in the process list."
        ),
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        create_admin(
            db,
            email=args.email.strip().lower(),
            full_name=args.name,
            password=args.password,
        )
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
