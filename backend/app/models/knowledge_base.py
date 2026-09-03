from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False
    )

    vector_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    index_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="knowledge_base_entries"
    )