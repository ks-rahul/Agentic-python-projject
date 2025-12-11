"""Agent schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AgentSettingBase(BaseModel):
    llm_provider: Optional[str] = "openai"
    llm_model: Optional[str] = "gpt-4"
    temperature: Optional[str] = "0.7"
    max_tokens: Optional[str] = "2048"
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    fallback_message: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentBase(BaseModel):
    name: str
    display_name: Optional[str] = None
    type: Optional[str] = "chatbot"
    description: Optional[str] = None


class AgentCreate(AgentBase):
    tenant_id: Optional[UUID] = None
    settings: Optional[AgentSettingBase] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class AgentSettingResponse(AgentSettingBase):
    id: UUID
    agent_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AgentResponse(AgentBase):
    id: UUID
    ai_agent_id: Optional[str] = None
    tenant_id: Optional[UUID] = None
    status: str
    settings: Optional[AgentSettingResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int


class AgentConfigureRequest(BaseModel):
    agent_id: UUID
    settings: AgentSettingBase


class KnowledgeBaseAttachRequest(BaseModel):
    agent_id: UUID
    knowledge_base_id: UUID


class AgentConfigurationResponse(BaseModel):
    agent: AgentResponse
    knowledge_bases: List[Dict[str, Any]]
    assistants: List[Dict[str, Any]]
    intent_configurations: List[Dict[str, Any]]
