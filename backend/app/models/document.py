from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_type import DocumentType
    from app.models.knowledge_base import KnowledgeBase
    from app.models.prediction import Prediction
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    file_size: Mapped[int] = mapped_column(nullable=False)

    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    document_type_id: Mapped[int] = mapped_column(
        ForeignKey("document_types.id"),
        nullable=False,
    )

    # ------------------------------------------------------- relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")

    document_type: Mapped["DocumentType"] = relationship(
        "DocumentType",
        back_populates="documents",
    )

    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    knowledge_base_entries: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name='{self.original_file_name}')>"
