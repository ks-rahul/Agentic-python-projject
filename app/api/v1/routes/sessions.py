"""Session management routes (MongoDB)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.db.mongodb import get_mongodb
from app.schemas.session import (
    SessionCreate, SessionResponse, SessionListResponse,
    EndSessionRequest, EndSessionResponse, ClearSessionResponse,
    SessionChatsResponse, FormCheckResponse
)
from app.services.session_service import SessionService
from app.core.security import get_current_user

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreate):
    """Create a new chat session."""
    session_service = SessionService()
    
    session = await session_service.create_session(
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        user_id=request.user_id,
        user_name=request.user_name,
        user_email=request.user_email,
        session_type=request.type
    )
    
    return session


@router.get("", response_model=SessionListResponse)
async def get_sessions(
    tenant_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    include_inactive: bool = False,
    type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sessions with optional filtering."""
    session_service = SessionService()
    
    result = await session_service.get_all_sessions(
        tenant_id=tenant_id or current_user.get("tenant_id"),
        limit=limit,
        page=page,
        include_inactive=include_inactive,
        session_type=type
    )
    
    return result


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by ID."""
    session_service = SessionService()
    session = await session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.get("/{session_id}/chats", response_model=SessionChatsResponse)
async def get_session_chats(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    decrypt: bool = False,
    include_metadata: bool = True
):
    """Get chat messages for a session."""
    session_service = SessionService()
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    result = await session_service.get_session_messages(
        session_id=session_id,
        limit=limit,
        offset=offset,
        decrypt=decrypt,
        include_metadata=include_metadata
    )
    
    return result


@router.post("/{session_id}/end", response_model=EndSessionResponse)
async def end_session(
    session_id: str,
    request: EndSessionRequest = EndSessionRequest()
):
    """End a chat session."""
    session_service = SessionService()
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if not session.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already ended"
        )
    
    result = await session_service.end_session(session_id, request.reason)
    return result


@router.post("/{session_id}/clear", response_model=ClearSessionResponse)
async def clear_session(
    session_id: str,
    request: EndSessionRequest = EndSessionRequest()
):
    """Clear and delete a session (playground only)."""
    session_service = SessionService()
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.get("type") != "playground":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clear is only allowed for playground sessions"
        )
    
    result = await session_service.clear_session(session_id)
    return result


@router.post("/{session_id}/clear-chat")
async def clear_session_chats(session_id: str):
    """Clear chat messages for a session."""
    session_service = SessionService()
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    result = await session_service.clear_chat_messages(session_id)
    return result


@router.get("/{session_id}/check-chat-form", response_model=FormCheckResponse)
async def check_chat_form(
    session_id: str,
    type: str = Query("check")
):
    """Check if lead form should be shown for session."""
    session_service = SessionService()
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    result = await session_service.get_session_form_data(session_id, type)
    return result
