from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    type_name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="document_type",
        cascade="all, delete-orphan"
    )