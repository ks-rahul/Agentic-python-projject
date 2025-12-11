"""Chat Builder schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChatBuilderBase(BaseModel):
    name: str
    description: Optional[str] = None
    widget_title: Optional[str] = "Chat with us"
    widget_subtitle: Optional[str] = None
    primary_color: Optional[str] = "#007bff"
    secondary_color: Optional[str] = "#6c757d"
    position: Optional[str] = "bottom-right"
    logo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    auto_open: Optional[bool] = False
    show_typing_indicator: Optional[bool] = True
    enable_file_upload: Optional[bool] = False
    enable_voice_input: Optional[bool] = False
    config: Optional[Dict[str, Any]] = None


class ChatBuilderCreate(ChatBuilderBase):
    tenant_id: UUID


class ChatBuilderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    widget_title: Optional[str] = None
    widget_subtitle: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    position: Optional[str] = None
    logo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    auto_open: Optional[bool] = None
    show_typing_indicator: Optional[bool] = None
    enable_file_upload: Optional[bool] = None
    enable_voice_input: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ChatBuilderResponse(ChatBuilderBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatBuilderListResponse(BaseModel):
    chat_builders: List[ChatBuilderResponse]
    total: int


class ConfigureChatBuilderRequest(BaseModel):
    chat_builder_id: UUID
    agent_ids: List[UUID]
