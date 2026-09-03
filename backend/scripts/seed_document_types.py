from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document_type import DocumentType
from app.constants.document_types import DocumentTypes


def seed_document_types(db: Session):

    document_types = [
        {
            "type_name": DocumentTypes.IMAGE,
            "description": "Image files"
        },
        {
            "type_name": DocumentTypes.VIDEO,
            "description": "Video files"
        },
        {
            "type_name": DocumentTypes.AUDIO,
            "description": "Audio files"
        },
        {
            "type_name": DocumentTypes.TEXT,
            "description": "Text documents"
        },
        {
            "type_name": DocumentTypes.REVIEW,
            "description": "Product or service reviews"
        }
    ]

    for data in document_types:

        exists = (
            db.query(DocumentType)
            .filter(
                DocumentType.type_name == data["type_name"]
            )
            .first()
        )

        if not exists:
            db.add(DocumentType(**data))

    db.commit()


if __name__ == "__main__":

    db = SessionLocal()

    try:
        seed_document_types(db)
        print("✅ Document types seeded successfully.")

    finally:
        db.close()