"""Human handoff routes for transferring conversations to human agents."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.services.session_service import SessionService
from app.core.logging import get_logger
from app.core.security import get_current_user

logger = get_logger(__name__)

router = APIRouter()


class HandoffRequest(BaseModel):
    session_id: str
    reason: str
    priority: str = "normal"  # high, normal, low
    user_message: Optional[str] = None
    metadata: Optional[dict] = {}


class AcceptHandoffRequest(BaseModel):
    handoff_id: str
    agent_id: str
    agent_name: str
    agent_email: Optional[str] = None
    metadata: Optional[dict] = {}


class HumanMessageRequest(BaseModel):
    session_id: str
    content: str
    agent_id: str
    metadata: Optional[dict] = {}


class EndHandoffRequest(BaseModel):
    session_id: str
    agent_id: str
    reason: str = "Conversation resolved"
    metadata: Optional[dict] = {}


class HandoffFilters(BaseModel):
    tenant_id: Optional[str] = None
    priority: Optional[str] = None
    limit: int = 50


@router.post("/request")
async def request_handoff(
    request: HandoffRequest,
    current_user: dict = Depends(get_current_user)
):
    """Request human handoff for a session."""
    session_service = SessionService()
    
    # Get session
    session = await session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if handoff is already active
    if session.get("is_human", False):
        return {
            "success": False,
            "message": "Human handoff is already active for this session",
            "handoff_id": None
        }
    
    # Create handoff request
    handoff_id = f"handoff_{int(datetime.utcnow().timestamp())}_{request.session_id[:8]}"
    
    handoff_data = {
        "handoff_id": handoff_id,
        "session_id": request.session_id,
        "tenant_id": session.get("tenant_id"),
        "agent_id": session.get("agent_id"),
        "reason": request.reason,
        "priority": request.priority,
        "requested_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "estimated_wait_time": _estimate_wait_time(request.priority),
        "metadata": {
            **request.metadata,
            "user_message": request.user_message,
            "message_count": session.get("metadata", {}).get("message_count", 0)
        }
    }
    
    # Enable human handoff on session
    await session_service.enable_human_handoff(request.session_id, handoff_data)
    
    logger.info(f"Human handoff requested: {handoff_id}")
    
    return {
        "success": True,
        "message": "Human handoff request submitted successfully",
        "handoff_id": handoff_id,
        "estimated_wait_time": handoff_data["estimated_wait_time"]
    }


@router.post("/accept")
async def accept_handoff(
    request: AcceptHandoffRequest,
    current_user: dict = Depends(get_current_user)
):
    """Accept a handoff request by human agent."""
    session_service = SessionService()
    
    # Find session with this handoff
    # In production, you'd have a proper handoff tracking system
    # For now, we'll update the session directly
    
    result = await session_service.accept_human_handoff(
        request.handoff_id,
        {
            "agent_id": request.agent_id,
            "agent_name": request.agent_name,
            "agent_email": request.agent_email,
            "accepted_at": datetime.utcnow().isoformat(),
            **request.metadata
        }
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handoff request not found or already processed"
        )
    
    logger.info(f"Human handoff accepted: {request.handoff_id} by {request.agent_name}")
    
    return {
        "success": True,
        "message": "Handoff request accepted successfully",
        "handoff_id": request.handoff_id
    }


@router.post("/message")
async def send_human_message(
    request: HumanMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message as a human agent."""
    session_service = SessionService()
    
    # Verify session exists and is in human handoff mode
    session = await session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if not session.get("is_human", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not in human handoff mode"
        )
    
    # Create human message
    message_id = await session_service.create_human_message(
        session_id=request.session_id,
        content=request.content,
        agent_id=request.agent_id,
        metadata=request.metadata
    )
    
    logger.info(f"Human message sent in session {request.session_id}")
    
    return {
        "success": True,
        "message": "Human message sent successfully",
        "message_id": message_id
    }


@router.post("/end")
async def end_handoff(
    request: EndHandoffRequest,
    current_user: dict = Depends(get_current_user)
):
    """End human handoff and return to AI."""
    session_service = SessionService()
    
    # Verify session exists
    session = await session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if not session.get("is_human", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not in human handoff mode"
        )
    
    # Disable human handoff
    await session_service.disable_human_handoff(
        request.session_id,
        reason=request.reason,
        metadata=request.metadata
    )
    
    logger.info(f"Human handoff ended for session {request.session_id}")
    
    return {
        "success": True,
        "message": "Human handoff ended successfully",
        "returned_to_ai": True
    }


@router.get("/pending")
async def get_pending_handoffs(
    tenant_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get pending handoff requests."""
    session_service = SessionService()
    
    handoffs = await session_service.get_pending_handoffs(
        tenant_id=tenant_id or current_user.get("tenant_id"),
        priority=priority,
        limit=limit
    )
    
    return {
        "handoffs": handoffs,
        "total": len(handoffs)
    }


@router.get("/stats")
async def get_handoff_stats(
    tenant_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get handoff statistics."""
    session_service = SessionService()
    
    stats = await session_service.get_handoff_stats(
        tenant_id=tenant_id or current_user.get("tenant_id")
    )
    
    return stats


def _estimate_wait_time(priority: str) -> int:
    """Estimate wait time in minutes based on priority."""
    base_times = {
        "high": 2,
        "normal": 5,
        "low": 10
    }
    return base_times.get(priority, 5)
