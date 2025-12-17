"""Chat service for AI conversations with RAG support."""
from typing import AsyncGenerator, Dict, Any, Optional, List
import uuid
import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.services.session_service import SessionService
from app.services.rag_service import get_rag_service, RAGService

logger = get_logger(__name__)


class ChatService:
    """Service for AI chat operations with RAG support."""
    
    def __init__(self):
        self.session_service = SessionService()
        self._rag_service: Optional[RAGService] = None
    
    @property
    def rag_service(self) -> RAGService:
        """Lazy load RAG service."""
        if self._rag_service is None:
            self._rag_service = get_rag_service()
        return self._rag_service
    
    async def stream_chat(
        self,
        agent_config: Dict[str, Any],
        session_id: str,
        user_query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat response from AI with RAG support."""
        message_id = str(uuid.uuid4())
        full_response = ""
        
        try:
            # Get chat history from session if not provided
            if chat_history is None:
                session_messages = await self.session_service.get_session_messages(
                    session_id=session_id,
                    limit=20
                )
                chat_history = [
                    {
                        "role": msg.get("message_type", "user"),
                        "content": msg.get("content", "")
                    }
                    for msg in session_messages.get("messages", [])
                ]
            
            # Use RAG service for chat
            async for event in self.rag_service.chat_with_rag(
                query=user_query,
                agent_config=agent_config,
                session_id=session_id,
                chat_history=chat_history
            ):
                if event["type"] == "chunk":
                    full_response += event.get("content", "")
                yield event
            
            # Save messages to session
            await self.update_chat_history(
                session_id=session_id,
                user_message=user_query,
                assistant_message=full_response
            )
            
        except Exception as e:
            logger.error(f"Error in chat stream: {e}", exc_info=True)
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
    
    async def generate_code(
        self,
        query: str,
        payload: Dict[str, Any],
        endpoints: Dict[str, Any],
        configurations: Dict[str, Any],
        base_url: str,
        action_name: List[str],
        fields_mapping: Dict[str, Any],
        tenant_id: str,
        connector_name: str,
        connector_id: str
    ) -> Dict[str, Any]:
        """Generate code for an assistant/connector using AI."""
        
        # Build the code generation prompt
        prompt = self._build_code_generation_prompt(
            query=query,
            endpoints=endpoints,
            configurations=configurations,
            base_url=base_url,
            action_name=action_name,
            fields_mapping=fields_mapping,
            connector_name=connector_name
        )
        
        system_prompt = """You are an expert Python developer specializing in API integrations.
Generate clean, well-documented Python code for API connectors.
The code should:
1. Handle authentication properly (API keys, OAuth, Bearer tokens)
2. Include proper error handling
3. Use async/await for HTTP requests
4. Include type hints
5. Be production-ready

Return ONLY the Python code, no explanations."""
        
        try:
            # Use RAG service for code generation
            generated_code = await self.rag_service.simple_chat(
                query=prompt,
                system_prompt=system_prompt,
                model=settings.CODE_GENERATION_MODEL or "gpt-4",
                provider="openai"
            )
            
            # Clean up the code (remove markdown code blocks if present)
            generated_code = self._clean_generated_code(generated_code)
            
            # Save the generated code
            code_path = self._get_code_path(tenant_id, connector_id)
            code_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(code_path, "w") as f:
                f.write(generated_code)
            
            logger.info(f"Generated code saved to: {code_path}")
            
            return {
                "status": "success",
                "code": generated_code,
                "path": str(code_path),
                "connector_name": connector_name,
                "actions": action_name
            }
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "code": None,
                "path": None
            }
    
    def _build_code_generation_prompt(
        self,
        query: str,
        endpoints: Dict[str, Any],
        configurations: Dict[str, Any],
        base_url: str,
        action_name: List[str],
        fields_mapping: Dict[str, Any],
        connector_name: str
    ) -> str:
        """Build prompt for code generation."""
        
        actions_info = ""
        if "actions" in endpoints:
            for action in endpoints["actions"]:
                actions_info += f"""
Action: {action.get('name', 'unknown')}
  Method: {action.get('method', 'GET')}
  Endpoint: {action.get('endpoint', '/')}
  Description: {action.get('description', '')}
  Parameters: {json.dumps(action.get('parameters', []), indent=2)}
"""
        
        prompt = f"""
Generate a Python connector class for the following API:

Connector Name: {connector_name}
Base URL: {base_url}
Description: {query}

Available Actions:
{actions_info}

Field Mappings:
{json.dumps(fields_mapping, indent=2)}

Requirements:
1. Create a class named `{connector_name.replace(' ', '')}Connector`
2. Implement each action as a method
3. Handle authentication based on the auth type
4. Include proper error handling and logging
5. Use httpx for async HTTP requests
6. Include docstrings for all methods

Generate the complete Python code:
"""
        return prompt
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean up generated code by removing markdown formatting."""
        # Remove markdown code blocks
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    def _get_code_path(self, tenant_id: str, connector_id: str) -> Path:
        """Get the path for storing generated code."""
        base_path = Path(settings.GENERATED_CODE_PATH or "generated_code")
        return base_path / f"tenant_{tenant_id}" / f"connector_{connector_id}.py"
    
    async def invoke_generated_code(
        self,
        code_path: str,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a method from generated code."""
        import importlib.util
        import inspect
        
        path = Path(code_path)
        if not path.exists():
            return {
                "status": "error",
                "error": "Code file not found"
            }
        
        try:
            # Load the module dynamically
            spec = importlib.util.spec_from_file_location("connector_module", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the connector class
            connector_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name.endswith("Connector"):
                    connector_class = obj
                    break
            
            if not connector_class:
                return {
                    "status": "error",
                    "error": "No connector class found in module"
                }
            
            # Instantiate and call the action
            connector = connector_class()
            
            if not hasattr(connector, action):
                return {
                    "status": "error",
                    "error": f"Action '{action}' not found in connector"
                }
            
            method = getattr(connector, action)
            
            # Check if method is async
            if inspect.iscoroutinefunction(method):
                result = await method(payload)
            else:
                result = method(payload)
            
            return {
                "status": "success",
                "action": action,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error invoking generated code: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
