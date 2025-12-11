"""Chat Builder models."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class ChatBuilderStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ChatBuilder(BaseModel, SoftDeleteMixin):
    """Chat Builder for widget configuration."""
    __tablename__ = "chat_builders"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ChatBuilderStatus), default=ChatBuilderStatus.DRAFT)
    
    # Widget Configuration
    widget_title = Column(String(255), default="Chat with us")
    widget_subtitle = Column(String(255), nullable=True)
    primary_color = Column(String(20), default="#007bff")
    secondary_color = Column(String(20), default="#6c757d")
    position = Column(String(20), default="bottom-right")
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Behavior
    auto_open = Column(Boolean, default=False)
    show_typing_indicator = Column(Boolean, default=True)
    enable_file_upload = Column(Boolean, default=False)
    enable_voice_input = Column(Boolean, default=False)
    
    # Additional config
    config = Column(JSON, nullable=True)

    # Relationships
    agents = relationship("Agent", secondary="chat_builder_agents", back_populates="chat_builders")


class ChatBuilderAgent(BaseModel):
    """Association between chat builders and agents."""
    __tablename__ = "chat_builder_agents"

    chat_builder_id = Column(UUID(as_uuid=True), ForeignKey("chat_builders.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
