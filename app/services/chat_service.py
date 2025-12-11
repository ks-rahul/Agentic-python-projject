"""Chat service for AI conversations."""
from typing import AsyncGenerator, Dict, Any, Optional
import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.services.session_service import SessionService

logger = get_logger(__name__)


class ChatService:
    """Service for AI chat operations."""
    
    def __init__(self):
        self.session_service = SessionService()
    
    async def stream_chat(
        self,
        agent_config: Dict[str, Any],
        session_id: str,
        user_query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat response from AI."""
        message_id = str(uuid.uuid4())
        
        try:
            # Get agent settings
            agent = agent_config.get("agent", {})
            agent_settings = agent.settings if hasattr(agent, 'settings') else {}
            
            # Get LLM configuration
            llm_provider = getattr(agent_settings, 'llm_provider', 'openai') if agent_settings else 'openai'
            llm_model = getattr(agent_settings, 'llm_model', 'gpt-4') if agent_settings else 'gpt-4'
            system_prompt = getattr(agent_settings, 'system_prompt', '') if agent_settings else ''
            
            # Yield start event
            yield {
                "type": "start",
                "message_id": message_id,
                "model": llm_model
            }
            
            # TODO: Implement actual LLM integration
            # For now, return a placeholder response
            response = f"This is a placeholder response for: {user_query}"
            
            # Stream response in chunks
            words = response.split()
            for word in words:
                yield {
                    "type": "chunk",
                    "content": word + " ",
                    "message_id": message_id
                }
            
            # Yield end event
            yield {
                "type": "end",
                "message_id": message_id,
                "full_response": response
            }
            
            # Save messages to session
            await self.update_chat_history(
                session_id=session_id,
                user_message=user_query,
                assistant_message=response
            )
            
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "message_id": message_id
            }
    
    async def update_chat_history(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> None:
        """Update chat history in session."""
        try:
            # Add user message
            await self.session_service.add_message(
                session_id=session_id,
                content=user_message,
                message_type="user"
            )
            
            # Add assistant message
            await self.session_service.add_message(
                session_id=session_id,
                content=assistant_message,
                message_type="assistant"
            )
            
        except Exception as e:
            logger.error(f"Error updating chat history: {e}")
