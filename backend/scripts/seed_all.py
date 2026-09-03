from app.db.session import SessionLocal
from scripts.seed_document_types import seed_document_types
from scripts.seed_roles import seed_roles

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_document_types(db)
        print("All seed data applied.")
    finally:
        db.close()
