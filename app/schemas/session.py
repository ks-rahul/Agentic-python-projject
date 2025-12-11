"""Session and Chat schemas for MongoDB."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    tenant_id: str
    agent_id: str
    agent_name: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    type: str = "chatbot"


class SessionUser(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class SessionMetadata(BaseModel):
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    token_usage: int = 0


class SessionResponse(BaseModel):
    session_id: str
    tenant_id: str
    agent_id: str
    agent_name: Optional[str] = None
    user: Optional[SessionUser] = None
    type: str
    is_active: bool
    is_human: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    metadata: SessionMetadata


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    pagination: Dict[str, int]


class EndSessionRequest(BaseModel):
    reason: Optional[str] = "Ended via API"


class EndSessionResponse(BaseModel):
    success: bool
    session_id: str
    summary: Dict[str, Any]
    reason: str
    timestamp: str


class ClearSessionResponse(BaseModel):
    success: bool
    session_id: str
    messages_cleared: int
    session_deleted: bool
    message: str
    timestamp: str


# Message schemas
class MessageMetadata(BaseModel):
    llm_model: Optional[str] = None
    processing_time: Optional[float] = None
    confidence: Optional[float] = None
    sources: Optional[List[Dict[str, Any]]] = None


class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    message_type: str
    content: str
    sequence_number: int
    token_count: int
    type: Optional[str] = None
    metadata: Optional[MessageMetadata] = None
    created_at: datetime


class SessionChatsResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]
    pagination: Dict[str, int]
    session: Dict[str, Any]
    timestamp: str


# Chat request/response
class ChatRequest(BaseModel):
    session_id: str
    user_query: str


class ChatChunk(BaseModel):
    type: str
    content: Optional[str] = None
    message_id: Optional[str] = None
    error: Optional[str] = None


class FormCheckResponse(BaseModel):
    session_id: str
    is_new_form: bool
    is_duplicate_check_to_show_form: bool
    message: str
    not_found: bool
    success: bool
