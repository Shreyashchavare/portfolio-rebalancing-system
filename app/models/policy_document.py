"""SQLAlchemy models for Policy RAG documents and chunks."""

from datetime import date, datetime, timezone
from enum import Enum
import json
from typing import Any, List, Optional
import numpy as np
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class PolicyDocumentType(str, Enum):
    """Supported policy document classifications."""

    INVESTMENT_POLICY = "INVESTMENT_POLICY"
    MANDATE = "MANDATE"
    ESG_EXCLUSION = "ESG_EXCLUSION"
    REGULATORY = "REGULATORY"


class PolicyStatus(str, Enum):
    """Lifecycle status of a policy document."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"


class PolicyDocument(Base):
    """Database entity representing an ingested policy document."""

    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    policy_family_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PolicyDocumentType.INVESTMENT_POLICY.value,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PolicyStatus.ACTIVE.value,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    chunks: Mapped[List["PolicyChunk"]] = relationship(
        "PolicyChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PolicyChunk.chunk_index",
    )

    @validates("file_path")
    def validate_file_path(self, key: str, value: str) -> str:
        """Validate that file_path is non-empty and contains no traversal sequences."""
        if not value or not value.strip():
            raise ValueError("file_path cannot be empty or whitespace.")
        if ".." in value:
            raise ValueError(f"Invalid file_path: path traversal '..' is prohibited: '{value}'")
        return value

    @property
    def document_id(self) -> str:
        """Alias property for document identifier."""
        return self.id

    @property
    def effective_policy_family_id(self) -> str:
        """Return explicit policy_family_id if set, or documented unmerged fallback."""
        if self.policy_family_id and self.policy_family_id.strip():
            return self.policy_family_id.strip()
        return f"LEGACY-DOC-{self.id}"

    def __repr__(self) -> str:
        return f"<PolicyDocument(id='{self.id}', family='{self.policy_family_id}', title='{self.title}', version='{self.version}', status='{self.status}')>"


class PolicyChunk(Base):
    """Database entity representing an embedded text chunk belonging to a policy document."""

    __tablename__ = "policy_chunks"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    document: Mapped["PolicyDocument"] = relationship(
        "PolicyDocument",
        back_populates="chunks",
    )

    @property
    def chunk_id(self) -> str:
        """Alias property for chunk identifier."""
        return self.id

    @property
    def embedding(self) -> List[float]:
        """Deserialize and validate embedding vector from JSON."""
        data = json.loads(self.embedding_json)
        if not isinstance(data, list):
            raise ValueError(f"Chunk {self.id} embedding_json must be a list, got {type(data).__name__}")
        return [float(x) for x in data]


    def set_embedding(self, vector: Any) -> None:
        """Serialize embedding vector to JSON string."""
        if hasattr(vector, "tolist"):
            self.embedding_json = json.dumps(vector.tolist())
        else:
            self.embedding_json = json.dumps(list(vector))

    def __repr__(self) -> str:
        return f"<PolicyChunk(id='{self.id}', doc_id='{self.document_id}', index={self.chunk_index})>"

