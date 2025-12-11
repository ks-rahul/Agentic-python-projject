"""Assistant schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AssistantBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class AssistantCreate(AssistantBase):
    tenant_id: UUID


class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class AssistantResponse(AssistantBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    status: str
    generated_code: Optional[str] = None
    code_language: Optional[str] = None
    deployed_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssistantListResponse(BaseModel):
    assistants: List[AssistantResponse]
    total: int


class AssistantConfigurationBase(BaseModel):
    config_key: str
    config_value: Optional[str] = None
    config_type: Optional[str] = "string"
    is_required: Optional[bool] = False
    oauth_config: Optional[Dict[str, Any]] = None


class AssistantConfigurationCreate(AssistantConfigurationBase):
    assistant_id: UUID


class AssistantConfigurationResponse(AssistantConfigurationBase):
    id: UUID
    assistant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SaveAssistantConfigurationRequest(BaseModel):
    assistant_id: UUID
    configurations: List[AssistantConfigurationBase]


class GenerateCodeRequest(BaseModel):
    assistant_id: UUID
    prompt: Optional[str] = None


class UpdateGeneratedCodeRequest(BaseModel):
    assistant_id: UUID
    code: str


class InvokePlaygroundRequest(BaseModel):
    assistant_id: UUID
    method_name: str
    parameters: Optional[Dict[str, Any]] = None


class DeployAssistantRequest(BaseModel):
    assistant_id: UUID
    deployment_config: Optional[Dict[str, Any]] = None


# Agent Assistant schemas
class AttachAssistantRequest(BaseModel):
    agent_id: UUID
    assistant_id: UUID
    required_tenant_auth: Optional[str] = None
    auth_configurations: Optional[Dict[str, Any]] = None


class DetachAssistantRequest(BaseModel):
    agent_id: UUID
    assistant_id: UUID


class UpdateAgentAssistantAuthRequest(BaseModel):
    agent_id: UUID
    assistant_id: UUID
    auth_credentials: Dict[str, Any]


# Intent Configuration schemas
class IntentConfigurationBase(BaseModel):
    intent_name: str
    intent_description: Optional[str] = None
    trigger_phrases: Optional[List[str]] = None
    response_template: Optional[str] = None
    functions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True


class IntentConfigurationCreate(IntentConfigurationBase):
    tenant_id: UUID
    agent_id: UUID
    assistant_id: Optional[UUID] = None


class IntentConfigurationUpdate(BaseModel):
    intent_name: Optional[str] = None
    intent_description: Optional[str] = None
    trigger_phrases: Optional[List[str]] = None
    response_template: Optional[str] = None
    functions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class IntentConfigurationResponse(IntentConfigurationBase):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    assistant_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntentConfigurationListResponse(BaseModel):
    configurations: List[IntentConfigurationResponse]
    total: int
