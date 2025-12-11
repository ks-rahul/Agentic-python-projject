"""Session service for MongoDB chat sessions."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.db.mongodb import get_sessions_collection, get_messages_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionService:
    """Service for chat session operations (MongoDB)."""
    
    async def create_session(
        self,
        tenant_id: str,
        agent_id: str,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        session_type: str = "chatbot"
    ) -> Dict[str, Any]:
        """Create a new chat session."""
        sessions = get_sessions_collection()
        
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "type": session_type,
            "user": {
                "user_id": user_id,
                "name": user_name,
                "email": user_email
            } if user_id else None,
            "connection_id": None,
            "encryption_keys": None,
            "start_time": now,
            "end_time": None,
            "is_active": True,
            "is_human": False,
            "metadata": {
                "created_at": now,
                "last_activity": now,
                "message_count": 0,
                "token_usage": 0
            }
        }
        
        await sessions.insert_one(session)
        
        logger.info(f"Session created: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        sessions = get_sessions_collection()
        return await sessions.find_one({"session_id": session_id})
    
    async def get_all_sessions(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        include_inactive: bool = False,
        session_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all sessions with filtering."""
        sessions = get_sessions_collection()
        
        query = {}
        if tenant_id:
            query["tenant_id"] = tenant_id
        if not include_inactive:
            query["is_active"] = True
        if session_type:
            query["type"] = session_type
        
        skip = (page - 1) * limit
        
        cursor = sessions.find(query).sort("metadata.last_activity", -1).skip(skip).limit(limit)
        session_list = await cursor.to_list(length=limit)
        
        total = await sessions.count_documents(query)
        
        return {
            "sessions": session_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
        }
    
    async def end_session(self, session_id: str, reason: str = "Ended via API") -> Dict[str, Any]:
        """End a chat session."""
        sessions = get_sessions_collection()
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        now = datetime.utcnow()
        duration = (now - session["start_time"]).total_seconds() * 1000
        
        await sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_active": False,
                    "end_time": now,
                    "metadata.last_activity": now
                }
            }
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "summary": {
                "duration": duration,
                "total_messages": session["metadata"]["message_count"]
            },
            "reason": reason,
            "timestamp": now.isoformat()
        }
    
    async def clear_session(self, session_id: str) -> Dict[str, Any]:
        """Clear and delete a session (playground only)."""
        sessions = get_sessions_collection()
        messages = get_messages_collection()
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        if session.get("type") != "playground":
            raise ValueError("Clear is only allowed for playground sessions")
        
        # Delete messages
        delete_result = await messages.delete_many({"session_id": session_id})
        
        # Delete session
        await sessions.delete_one({"session_id": session_id})
        
        return {
            "success": True,
            "session_id": session_id,
            "messages_cleared": delete_result.deleted_count,
            "session_deleted": True,
            "message": "Session and messages deleted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def clear_chat_messages(self, session_id: str) -> Dict[str, Any]:
        """Clear chat messages for a session."""
        sessions = get_sessions_collection()
        messages = get_messages_collection()
        
        delete_result = await messages.delete_many({"session_id": session_id})
        
        # Reset message count
        await sessions.update_one(
            {"session_id": session_id},
            {"$set": {"metadata.message_count": 0}}
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "messages_cleared": delete_result.deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
        decrypt: bool = False,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Get messages for a session."""
        messages = get_messages_collection()
        session = await self.get_session(session_id)
        
        cursor = (
            messages.find({"session_id": session_id})
            .sort("sequence_number", 1)
            .skip(offset)
            .limit(limit)
        )
        
        message_list = await cursor.to_list(length=limit)
        
        return {
            "session_id": session_id,
            "messages": message_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(message_list)
            },
            "session": {
                "tenant_id": session["tenant_id"],
                "agent_id": session["agent_id"],
                "is_active": session["is_active"],
                "message_count": session["metadata"]["message_count"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_session_form_data(self, session_id: str, check_type: str = "check") -> Dict[str, Any]:
        """Get form data for session."""
        session = await self.get_session(session_id)
        if not session:
            return {
                "session_id": session_id,
                "is_new_form": False,
                "is_duplicate_check_to_show_form": False,
                "message": "Session not found",
                "not_found": True,
                "success": False
            }
        
        # Check for existing lead form message
        messages = get_messages_collection()
        lead_form_msg = await messages.find_one({
            "session_id": session_id,
            "type": "leadForm"
        })
        
        if not lead_form_msg:
            return {
                "session_id": session_id,
                "is_new_form": True,
                "is_duplicate_check_to_show_form": False,
                "message": "Lead form can be shown",
                "not_found": False,
                "success": True
            }
        
        return {
            "session_id": session_id,
            "is_new_form": False,
            "is_duplicate_check_to_show_form": False,
            "message": "Lead form already exists",
            "not_found": False,
            "success": True
        }
    
    async def add_message(
        self,
        session_id: str,
        content: str,
        message_type: str,
        token_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a message to a session."""
        sessions = get_sessions_collection()
        messages = get_messages_collection()
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        sequence_number = session["metadata"]["message_count"] + 1
        
        message = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "content": content,
            "message_type": message_type,
            "sequence_number": sequence_number,
            "token_count": token_count,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        await messages.insert_one(message)
        
        # Update session
        await sessions.update_one(
            {"session_id": session_id},
            {
                "$inc": {"metadata.message_count": 1, "metadata.token_usage": token_count},
                "$set": {"metadata.last_activity": datetime.utcnow()}
            }
        )
        
        return message
