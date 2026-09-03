from sqlalchemy.orm import Session

from app.constants.roles import Roles
from app.db.session import SessionLocal
from app.models.role import Role


def seed_roles(db: Session) -> None:
    """Idempotent — safe to run on every deploy."""

    roles = [
        {
            "role_name": Roles.ADMIN,
            "description": "Full access: user management, audit logs, deletion.",
        },
        {
            "role_name": Roles.ANALYST,
            "description": "Can upload, run analysis and generate reports.",
        },
        {
            "role_name": Roles.USER,
            "description": "Can upload and view own results.",
        },
    ]

    for data in roles:
        exists = (
            db.query(Role)
            .filter(Role.role_name == data["role_name"])
            .first()
        )
        if not exists:
            db.add(Role(**data))
            print(f"  + created role: {data['role_name']}")

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_roles(db)
        print("Roles seeded successfully.")
    finally:
        db.close()
