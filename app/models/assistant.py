"""Assistant models."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin, GUID


class AssistantStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class Assistant(BaseModel, SoftDeleteMixin):
    """Assistant model for custom integrations."""
    __tablename__ = "assistants"

    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=False)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(255), nullable=True)
    status = Column(Enum(AssistantStatus), default=AssistantStatus.DRAFT)
    
    # Code generation
    generated_code = Column(Text, nullable=True)
    code_language = Column(String(50), default="python")
    
    # Deployment
    deployed_at = Column(String(255), nullable=True)
    deployment_config = Column(JSON, nullable=True)

    # Relationships
    agents = relationship("Agent", secondary="agent_assistants", back_populates="assistants")
    agent_assistants = relationship("AgentAssistant", back_populates="assistant")
    configurations = relationship("AssistantConfiguration", back_populates="assistant")


class AssistantConfiguration(BaseModel):
    """Configuration for assistants."""
    __tablename__ = "assistant_configurations"

    assistant_id = Column(GUID(), ForeignKey("assistants.id"), nullable=False)
    config_key = Column(String(255), nullable=False)
    config_value = Column(Text, nullable=True)
    config_type = Column(String(50), default="string")
    is_required = Column(Boolean, default=False)
    oauth_config = Column(JSON, nullable=True)

    # Relationships
    assistant = relationship("Assistant", back_populates="configurations")


class AssistantIntentConfiguration(BaseModel, SoftDeleteMixin):
    """Intent configuration for assistants."""
    __tablename__ = "assistant_intent_configurations"

    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(GUID(), ForeignKey("agents.id"), nullable=False)
    assistant_id = Column(GUID(), ForeignKey("assistants.id"), nullable=True)
    
    intent_name = Column(String(255), nullable=False)
    intent_description = Column(Text, nullable=True)
    trigger_phrases = Column(JSON, nullable=True)
    response_template = Column(Text, nullable=True)
    functions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    agent = relationship("Agent", back_populates="intent_configurations")
