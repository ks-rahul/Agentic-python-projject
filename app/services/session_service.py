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

    async def update_session_encryption(
        self,
        session_id: str,
        encryption_data: Dict[str, Any]
    ) -> bool:
        """Update session encryption key during handshake."""
        sessions = get_sessions_collection()
        
        result = await sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "encryption_key": encryption_data.get("encryption_key"),
                    "key_shared_at": encryption_data.get("key_shared_at"),
                    "metadata.last_activity": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def enable_human_handoff(
        self,
        session_id: str,
        handoff_data: Dict[str, Any]
    ) -> bool:
        """Enable human handoff for session."""
        sessions = get_sessions_collection()
        
        result = await sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_human": True,
                    "handoff_data": handoff_data,
                    "metadata.last_activity": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Human handoff enabled for session {session_id}")
        return result.modified_count > 0
    
    async def disable_human_handoff(
        self,
        session_id: str,
        reason: str = "Conversation resolved",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Disable human handoff for session."""
        sessions = get_sessions_collection()
        
        result = await sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_human": False,
                    "handoff_data.status": "completed",
                    "handoff_data.completed_at": datetime.utcnow().isoformat(),
                    "handoff_data.resolution": reason,
                    "metadata.last_activity": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Human handoff disabled for session {session_id}")
        return result.modified_count > 0
    
    async def accept_human_handoff(
        self,
        handoff_id: str,
        agent_data: Dict[str, Any]
    ) -> bool:
        """Accept a human handoff request."""
        sessions = get_sessions_collection()
        
        result = await sessions.update_one(
            {"handoff_data.handoff_id": handoff_id, "handoff_data.status": "pending"},
            {
                "$set": {
                    "handoff_data.status": "accepted",
                    "handoff_data.human_agent": agent_data,
                    "metadata.last_activity": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def create_human_message(
        self,
        session_id: str,
        content: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a message from human agent."""
        message = await self.add_message(
            session_id=session_id,
            content=content,
            message_type="human",
            metadata={
                **(metadata or {}),
                "human_agent_id": agent_id
            }
        )
        return message["message_id"]
    
    async def get_pending_handoffs(
        self,
        tenant_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get pending handoff requests."""
        sessions = get_sessions_collection()
        
        query = {
            "is_human": True,
            "handoff_data.status": "pending"
        }
        
        if tenant_id:
            query["tenant_id"] = tenant_id
        if priority:
            query["handoff_data.priority"] = priority
        
        cursor = sessions.find(query).sort("handoff_data.requested_at", 1).limit(limit)
        results = await cursor.to_list(length=limit)
        
        return [r.get("handoff_data", {}) for r in results]
    
    async def get_handoff_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get handoff statistics."""
        sessions = get_sessions_collection()
        
        query = {"handoff_data": {"$exists": True}}
        if tenant_id:
            query["tenant_id"] = tenant_id
        
        total = await sessions.count_documents(query)
        pending = await sessions.count_documents({**query, "handoff_data.status": "pending"})
        accepted = await sessions.count_documents({**query, "handoff_data.status": "accepted"})
        completed = await sessions.count_documents({**query, "handoff_data.status": "completed"})
        
        return {
            "total": total,
            "pending": pending,
            "accepted": accepted,
            "completed": completed,
            "by_priority": {
                "high": await sessions.count_documents({**query, "handoff_data.priority": "high"}),
                "normal": await sessions.count_documents({**query, "handoff_data.priority": "normal"}),
                "low": await sessions.count_documents({**query, "handoff_data.priority": "low"})
            }
        }
    
    async def get_session_stats(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get session statistics."""
        sessions = get_sessions_collection()
        
        time_ranges = {
            "1h": 1 * 60 * 60,
            "24h": 24 * 60 * 60,
            "7d": 7 * 24 * 60 * 60,
            "30d": 30 * 24 * 60 * 60
        }
        
        seconds = time_ranges.get(time_range, time_ranges["24h"])
        start_time = datetime.utcnow().timestamp() - seconds
        start_datetime = datetime.fromtimestamp(start_time)
        
        total = await sessions.count_documents({})
        active = await sessions.count_documents({"is_active": True})
        in_range = await sessions.count_documents({"start_time": {"$gte": start_datetime}})
        
        return {
            "total": total,
            "active": active,
            "in_range": in_range,
            "time_range": time_range
        }
    
    async def get_message_stats(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get message statistics."""
        messages = get_messages_collection()
        
        time_ranges = {
            "1h": 1 * 60 * 60,
            "24h": 24 * 60 * 60,
            "7d": 7 * 24 * 60 * 60,
            "30d": 30 * 24 * 60 * 60
        }
        
        seconds = time_ranges.get(time_range, time_ranges["24h"])
        start_time = datetime.utcnow().timestamp() - seconds
        start_datetime = datetime.fromtimestamp(start_time)
        
        total = await messages.count_documents({})
        in_range = await messages.count_documents({"created_at": {"$gte": start_datetime}})
        
        return {
            "total": total,
            "in_range": in_range,
            "time_range": time_range
        }
