"""WebSocket message handlers."""
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime

from app.core.logging import get_logger
from app.websocket.manager import get_connection_manager
from app.services.session_service import SessionService
from app.services.chat_service import ChatService

logger = get_logger(__name__)


class WebSocketHandler:
    """Handler for WebSocket messages."""
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.session_service = SessionService()
        self.chat_service = ChatService()
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        session_id: str,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        """Handle a WebSocket connection lifecycle."""
        await self.manager.connect(websocket, session_id, tenant_id, agent_id)
        
        try:
            # Send connection confirmation
            await websocket.send_json({
                "type": "connected",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Listen for messages
            while True:
                data = await websocket.receive_text()
                await self.handle_message(websocket, session_id, data)
                
        except WebSocketDisconnect:
            self.manager.disconnect(session_id)
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {session_id}: {e}")
            self.manager.disconnect(session_id)
    
    async def handle_message(
        self,
        websocket: WebSocket,
        session_id: str,
        raw_data: str
    ):
        """Handle an incoming WebSocket message."""
        try:
            data = json.loads(raw_data)
            message_type = data.get("type", "message")
            
            if message_type == "message":
                await self.handle_chat_message(websocket, session_id, data)
            elif message_type == "typing":
                await self.handle_typing(session_id, data)
            elif message_type == "ping":
                await self.handle_ping(websocket)
            elif message_type == "handoff_request":
                await self.handle_handoff_request(session_id, data)
            elif message_type == "human_message":
                await self.handle_human_message(session_id, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "error": "Invalid JSON"
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
    
    async def handle_chat_message(
        self,
        websocket: WebSocket,
        session_id: str,
        data: Dict[str, Any]
    ):
        """Handle a chat message and stream AI response."""
        content = data.get("content", "")
        agent_config = data.get("agent_config", {})
        
        if not content:
            await websocket.send_json({
                "type": "error",
                "error": "Message content is required"
            })
            return
        
        # Send acknowledgment
        await websocket.send_json({
            "type": "message_received",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Stream AI response
        try:
            async for event in self.chat_service.stream_chat(
                agent_config=agent_config,
                session_id=session_id,
                user_query=content
            ):
                await websocket.send_json(event)
                
        except Exception as e:
            logger.error(f"Error streaming chat response: {e}")
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
    
    async def handle_typing(self, session_id: str, data: Dict[str, Any]):
        """Handle typing indicator."""
        is_typing = data.get("is_typing", False)
        
        # Get session to find if there's a human agent
        session = await self.session_service.get_session(session_id)
        
        if session and session.get("is_human"):
            # Notify human agent about typing
            handoff_data = session.get("handoff_data", {})
            human_agent = handoff_data.get("human_agent", {})
            agent_id = human_agent.get("agent_id")
            
            if agent_id:
                await self.manager.send_to_human_agent({
                    "type": "user_typing",
                    "session_id": session_id,
                    "is_typing": is_typing
                }, agent_id)
    
    async def handle_ping(self, websocket: WebSocket):
        """Handle ping message."""
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def handle_handoff_request(
        self,
        session_id: str,
        data: Dict[str, Any]
    ):
        """Handle human handoff request."""
        reason = data.get("reason", "User requested human agent")
        priority = data.get("priority", "normal")
        
        # Enable human handoff on session
        handoff_id = f"handoff_{int(datetime.utcnow().timestamp())}_{session_id[:8]}"
        
        handoff_data = {
            "handoff_id": handoff_id,
            "session_id": session_id,
            "reason": reason,
            "priority": priority,
            "requested_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        await self.session_service.enable_human_handoff(session_id, handoff_data)
        
        # Notify the user
        await self.manager.send_personal_message({
            "type": "handoff_initiated",
            "handoff_id": handoff_id,
            "message": "Connecting you with a human agent...",
            "estimated_wait": "2-5 minutes"
        }, session_id)
        
        # Broadcast to available human agents
        # In production, this would use a proper queue/notification system
        logger.info(f"Human handoff requested: {handoff_id}")
    
    async def handle_human_message(
        self,
        session_id: str,
        data: Dict[str, Any]
    ):
        """Handle message from human agent."""
        content = data.get("content", "")
        agent_id = data.get("agent_id")
        
        if not content or not agent_id:
            return
        
        # Add message to session
        await self.session_service.add_message(
            session_id=session_id,
            content=content,
            message_type="human",
            metadata={"human_agent_id": agent_id}
        )
        
        # Send to user
        await self.manager.send_personal_message({
            "type": "message",
            "content": content,
            "sender": "human",
            "timestamp": datetime.utcnow().isoformat()
        }, session_id)


class HumanAgentHandler:
    """Handler for human agent WebSocket connections."""
    
    def __init__(self):
        self.manager = get_connection_manager()
        self.session_service = SessionService()
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        agent_id: str
    ):
        """Handle human agent WebSocket connection."""
        await self.manager.connect_human_agent(websocket, agent_id)
        
        try:
            await websocket.send_json({
                "type": "connected",
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            while True:
                data = await websocket.receive_text()
                await self.handle_message(websocket, agent_id, data)
                
        except WebSocketDisconnect:
            self.manager.disconnect_human_agent(agent_id)
        except Exception as e:
            logger.error(f"Human agent WebSocket error: {e}")
            self.manager.disconnect_human_agent(agent_id)
    
    async def handle_message(
        self,
        websocket: WebSocket,
        agent_id: str,
        raw_data: str
    ):
        """Handle message from human agent."""
        try:
            data = json.loads(raw_data)
            message_type = data.get("type")
            
            if message_type == "accept_handoff":
                await self.handle_accept_handoff(agent_id, data)
            elif message_type == "message":
                await self.handle_send_message(agent_id, data)
            elif message_type == "end_handoff":
                await self.handle_end_handoff(agent_id, data)
            elif message_type == "typing":
                await self.handle_typing(agent_id, data)
                
        except Exception as e:
            logger.error(f"Error handling human agent message: {e}")
    
    async def handle_accept_handoff(self, agent_id: str, data: Dict[str, Any]):
        """Handle handoff acceptance."""
        handoff_id = data.get("handoff_id")
        agent_name = data.get("agent_name", "Support Agent")
        
        result = await self.session_service.accept_human_handoff(
            handoff_id,
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "accepted_at": datetime.utcnow().isoformat()
            }
        )
        
        if result:
            # Notify user
            # Would need to get session_id from handoff_id
            logger.info(f"Handoff {handoff_id} accepted by {agent_name}")
    
    async def handle_send_message(self, agent_id: str, data: Dict[str, Any]):
        """Handle message from human agent to user."""
        session_id = data.get("session_id")
        content = data.get("content")
        
        if session_id and content:
            await self.session_service.add_message(
                session_id=session_id,
                content=content,
                message_type="human",
                metadata={"human_agent_id": agent_id}
            )
            
            await self.manager.send_personal_message({
                "type": "message",
                "content": content,
                "sender": "human",
                "timestamp": datetime.utcnow().isoformat()
            }, session_id)
    
    async def handle_end_handoff(self, agent_id: str, data: Dict[str, Any]):
        """Handle ending a handoff."""
        session_id = data.get("session_id")
        reason = data.get("reason", "Conversation resolved")
        
        if session_id:
            await self.session_service.disable_human_handoff(session_id, reason)
            
            await self.manager.send_personal_message({
                "type": "handoff_ended",
                "message": "You are now chatting with our AI assistant again.",
                "reason": reason
            }, session_id)
    
    async def handle_typing(self, agent_id: str, data: Dict[str, Any]):
        """Handle typing indicator from human agent."""
        session_id = data.get("session_id")
        is_typing = data.get("is_typing", False)
        
        if session_id:
            await self.manager.send_personal_message({
                "type": "agent_typing",
                "is_typing": is_typing
            }, session_id)
