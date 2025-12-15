"""Knowledge Base model."""
from sqlalchemy import Column, String, Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin, GUID


class KnowledgeBaseStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TrainingStatus(str, enum.Enum):
    PENDING = "pending"
    TRAINING = "training"
    TRAINED = "trained"
    FAILED = "failed"


class RetrievalStrategy(str, enum.Enum):
    SIMILARITY = "similarity"
    MMR = "mmr"
    HYBRID = "hybrid"


class KnowledgeBase(BaseModel, SoftDeleteMixin):
    """Knowledge Base for RAG system."""
    __tablename__ = "knowledge_bases"

    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    short_description = Column(Text, nullable=True)
    
    # RAG Configuration
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    max_response_tokens = Column(Integer, default=2048)
    retrieval_strategy = Column(Enum(RetrievalStrategy), default=RetrievalStrategy.SIMILARITY)
    retrieved_chunks = Column(Integer, default=5)
    
    status = Column(Enum(KnowledgeBaseStatus), default=KnowledgeBaseStatus.ACTIVE)
    training_status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING)

    # Relationships
    documents = relationship("Document", back_populates="knowledge_base")
    website_scrapes = relationship("WebsiteScrape", back_populates="knowledge_base")
    agents = relationship("AgentKnowledgeBase", back_populates="knowledge_base")
