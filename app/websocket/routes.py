"""WebSocket routes for real-time chat."""
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.websocket.handlers import WebSocketHandler, HumanAgentHandler
from app.websocket.manager import get_connection_manager
from app.core.logging import get_logger
from app.core.security import decode_token

logger = get_logger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.websocket("/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    tenant_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time chat.
    
    Connect with: ws://host/ws/chat/{session_id}?tenant_id=xxx&agent_id=xxx
    
    Message format:
    {
        "type": "message",
        "content": "Hello",
        "agent_config": {...}  // Optional, for AI configuration
    }
    
    Response events:
    - connected: Connection established
    - message_received: Message acknowledged
    - start: AI response starting
    - chunk: AI response chunk
    - end: AI response complete
    - error: Error occurred
    """
    handler = WebSocketHandler()
    await handler.handle_connection(
        websocket=websocket,
        session_id=session_id,
        tenant_id=tenant_id,
        agent_id=agent_id
    )


@router.websocket("/human-agent/{agent_id}")
async def websocket_human_agent_endpoint(
    websocket: WebSocket,
    agent_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for human agents (support staff).
    
    Connect with: ws://host/ws/human-agent/{agent_id}?token=xxx
    
    Message types:
    - accept_handoff: Accept a pending handoff
    - message: Send message to user
    - end_handoff: End handoff and return to AI
    - typing: Typing indicator
    """
    # Validate token for human agents
    if token:
        try:
            payload = decode_token(token)
            # Verify agent has permission for human handoff
            # This is a simplified check - production would be more robust
        except Exception as e:
            await websocket.close(code=4001, reason="Invalid token")
            return
    
    handler = HumanAgentHandler()
    await handler.handle_connection(
        websocket=websocket,
        agent_id=agent_id
    )


@router.get("/connections")
async def get_connections():
    """Get current WebSocket connection statistics."""
    manager = get_connection_manager()
    return manager.get_connection_count()


@router.get("/sessions")
async def get_active_sessions(tenant_id: Optional[str] = None):
    """Get list of active WebSocket sessions."""
    manager = get_connection_manager()
    sessions = manager.get_active_sessions(tenant_id)
    return {
        "sessions": sessions,
        "count": len(sessions)
    }
