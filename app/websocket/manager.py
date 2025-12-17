"""WebSocket connection manager."""
from typing import Dict, List, Optional, Set
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        # session_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        
        # tenant_id -> set of session_ids
        self.tenant_sessions: Dict[str, Set[str]] = {}
        
        # agent_id -> set of session_ids
        self.agent_sessions: Dict[str, Set[str]] = {}
        
        # Human agent connections (for handoff)
        self.human_agent_connections: Dict[str, WebSocket] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[session_id] = websocket
        
        if tenant_id:
            if tenant_id not in self.tenant_sessions:
                self.tenant_sessions[tenant_id] = set()
            self.tenant_sessions[tenant_id].add(session_id)
        
        if agent_id:
            if agent_id not in self.agent_sessions:
                self.agent_sessions[agent_id] = set()
            self.agent_sessions[agent_id].add(session_id)
        
        logger.info(f"WebSocket connected: session={session_id}, tenant={tenant_id}, agent={agent_id}")
    
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # Remove from tenant sessions
        for tenant_id, sessions in self.tenant_sessions.items():
            sessions.discard(session_id)
        
        # Remove from agent sessions
        for agent_id, sessions in self.agent_sessions.items():
            sessions.discard(session_id)
        
        logger.info(f"WebSocket disconnected: session={session_id}")
    
    async def connect_human_agent(
        self,
        websocket: WebSocket,
        agent_id: str
    ):
        """Connect a human agent for handoff support."""
        await websocket.accept()
        self.human_agent_connections[agent_id] = websocket
        logger.info(f"Human agent connected: {agent_id}")
    
    def disconnect_human_agent(self, agent_id: str):
        """Disconnect a human agent."""
        if agent_id in self.human_agent_connections:
            del self.human_agent_connections[agent_id]
        logger.info(f"Human agent disconnected: {agent_id}")
    
    async def send_personal_message(
        self,
        message: Dict,
        session_id: str
    ):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def send_to_human_agent(
        self,
        message: Dict,
        agent_id: str
    ):
        """Send a message to a human agent."""
        if agent_id in self.human_agent_connections:
            websocket = self.human_agent_connections[agent_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to human agent {agent_id}: {e}")
                self.disconnect_human_agent(agent_id)
    
    async def broadcast_to_tenant(
        self,
        message: Dict,
        tenant_id: str
    ):
        """Broadcast a message to all sessions in a tenant."""
        if tenant_id in self.tenant_sessions:
            for session_id in self.tenant_sessions[tenant_id]:
                await self.send_personal_message(message, session_id)
    
    async def broadcast_to_agent(
        self,
        message: Dict,
        agent_id: str
    ):
        """Broadcast a message to all sessions using an agent."""
        if agent_id in self.agent_sessions:
            for session_id in self.agent_sessions[agent_id]:
                await self.send_personal_message(message, session_id)
    
    def get_active_sessions(self, tenant_id: Optional[str] = None) -> List[str]:
        """Get list of active session IDs."""
        if tenant_id:
            return list(self.tenant_sessions.get(tenant_id, set()))
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> Dict[str, int]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "human_agents": len(self.human_agent_connections),
            "tenants": len(self.tenant_sessions),
            "agents": len(self.agent_sessions)
        }
    
    def is_connected(self, session_id: str) -> bool:
        """Check if a session is connected."""
        return session_id in self.active_connections


# Singleton instance
_connection_manager = None


def get_connection_manager() -> ConnectionManager:
    """Get the connection manager singleton."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
