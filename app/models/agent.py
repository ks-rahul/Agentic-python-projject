"""Agent models."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AgentType(str, enum.Enum):
    CHATBOT = "chatbot"
    ASSISTANT = "assistant"
    WORKFLOW = "workflow"


class Agent(BaseModel, SoftDeleteMixin):
    """AI Agent model."""
    __tablename__ = "agents"

    ai_agent_id = Column(String(255), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    type = Column(Enum(AgentType), default=AgentType.CHATBOT)
    description = Column(Text, nullable=True)
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT)

    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    settings = relationship("AgentSetting", back_populates="agent", uselist=False)
    knowledge_bases = relationship("AgentKnowledgeBase", back_populates="agent")
    assistants = relationship("Assistant", secondary="agent_assistants", back_populates="agents")
    agent_assistants = relationship("AgentAssistant", back_populates="agent")
    chat_builders = relationship("ChatBuilder", secondary="chat_builder_agents", back_populates="agents")
    lead_form = relationship("LeadForm", back_populates="agent", uselist=False)
    intent_configurations = relationship("AssistantIntentConfiguration", back_populates="agent")


class AgentSetting(BaseModel):
    """Agent settings and configuration."""
    __tablename__ = "agent_settings"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # LLM Settings
    llm_provider = Column(String(50), default="openai")
    llm_model = Column(String(100), default="gpt-4")
    temperature = Column(String(10), default="0.7")
    max_tokens = Column(String(10), default="2048")
    
    # Agent Behavior
    system_prompt = Column(Text, nullable=True)
    welcome_message = Column(Text, nullable=True)
    fallback_message = Column(Text, nullable=True)
    
    # Industry/Role
    industry = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
    
    # Additional config as JSON
    config = Column(JSON, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="settings")


class AgentKnowledgeBase(BaseModel):
    """Association between agents and knowledge bases."""
    __tablename__ = "agent_knowledge_bases"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="knowledge_bases")
    knowledge_base = relationship("KnowledgeBase", back_populates="agents")


class AgentAssistant(BaseModel):
    """Association between agents and assistants with auth config."""
    __tablename__ = "agent_assistants"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    assistant_id = Column(UUID(as_uuid=True), ForeignKey("assistants.id"), nullable=False)
    required_tenant_auth = Column(String(50), nullable=True)
    auth_configurations = Column(JSON, nullable=True)
    auth_credentials = Column(JSON, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="agent_assistants")
    assistant = relationship("Assistant", back_populates="agent_assistants")
