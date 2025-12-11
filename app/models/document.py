"""Document model."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    HTML = "html"
    MD = "md"


class SourceType(str, enum.Enum):
    UPLOAD = "upload"
    WEBSITE = "website"
    API = "api"


class Document(BaseModel, SoftDeleteMixin):
    """Document model for knowledge base."""
    __tablename__ = "documents"

    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)
    type = Column(Enum(DocumentType), nullable=True)
    source_type = Column(Enum(SourceType), default=SourceType.UPLOAD)
    website_scrapes_id = Column(UUID(as_uuid=True), ForeignKey("website_scrapes.id"), nullable=True)
    document = Column(String(500), nullable=True)  # File path or URL
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
