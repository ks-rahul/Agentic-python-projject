"""RAG (Retrieval Augmented Generation) service for AI conversations."""
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Optional imports - gracefully handle if not installed
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. Install with: pip install openai")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic not installed. Install with: pip install anthropic")

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not installed. Install with: pip install pinecone-client")


class RAGService:
    """Service for RAG-based AI conversations."""
    
    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None
        self._pinecone_index = None
        self._embedding_model = None
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None and OPENAI_AVAILABLE:
            api_key = settings.OPENAI_API_KEY
            if api_key:
                self._openai_client = AsyncOpenAI(api_key=api_key)
        return self._openai_client
    
    @property
    def anthropic_client(self):
        """Lazy load Anthropic client."""
        if self._anthropic_client is None and ANTHROPIC_AVAILABLE:
            api_key = settings.ANTHROPIC_API_KEY
            if api_key:
                self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._anthropic_client
    
    @property
    def pinecone_index(self):
        """Lazy load Pinecone index."""
        if self._pinecone_index is None and PINECONE_AVAILABLE:
            api_key = settings.PINECONE_API_KEY
            index_name = settings.PINECONE_INDEX_NAME
            if api_key and index_name:
                pc = Pinecone(api_key=api_key)
                self._pinecone_index = pc.Index(index_name)
        return self._pinecone_index
    
    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for text using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")
        
        response = await self.openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL or "text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    async def retrieve_context(
        self,
        query: str,
        tenant_id: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context from vector store."""
        if not self.pinecone_index:
            logger.warning("Pinecone not configured, skipping context retrieval")
            return []
        
        try:
            # Get query embeddings
            query_embedding = await self.get_embeddings(query)
            
            # Build filter
            filter_dict = {"tenant_id": {"$eq": tenant_id}}
            if knowledge_base_ids:
                filter_dict["knowledge_base_id"] = {"$in": knowledge_base_ids}
            
            # Query Pinecone
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict,
                namespace=tenant_id
            )
            
            contexts = []
            for match in results.matches:
                contexts.append({
                    "content": match.metadata.get("text", ""),
                    "score": match.score,
                    "source": match.metadata.get("original_filename", "Unknown"),
                    "document_id": match.metadata.get("app_document_id"),
                })
            
            return contexts
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def _build_system_prompt(
        self,
        base_prompt: str,
        contexts: List[Dict[str, Any]],
        agent_settings: Dict[str, Any]
    ) -> str:
        """Build system prompt with context."""
        context_text = ""
        if contexts:
            context_text = "\n\n## Relevant Context:\n"
            for i, ctx in enumerate(contexts, 1):
                context_text += f"\n[Source {i}: {ctx['source']}]\n{ctx['content']}\n"
        
        system_prompt = base_prompt or "You are a helpful AI assistant."
        
        if context_text:
            system_prompt += f"""

{context_text}

## Instructions:
- Use the provided context to answer questions accurately
- If the context doesn't contain relevant information, say so
- Always cite sources when using information from the context
- Be helpful, concise, and accurate
"""
        
        return system_prompt
    
    async def stream_chat_openai(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat response from OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")
        
        stream = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def stream_chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat response from Anthropic."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not configured")
        
        # Convert messages format for Anthropic
        anthropic_messages = []
        for msg in messages:
            if msg["role"] != "system":
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        async with self.anthropic_client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=anthropic_messages
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def chat_with_rag(
        self,
        query: str,
        agent_config: Dict[str, Any],
        session_id: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Main RAG chat method with streaming."""
        import uuid
        message_id = str(uuid.uuid4())
        
        try:
            # Extract agent settings
            agent = agent_config.get("agent", {})
            agent_settings = agent.get("settings", {}) if isinstance(agent, dict) else {}
            
            # Get LLM configuration
            llm_provider = agent_settings.get("llm_provider", "openai")
            llm_model = agent_settings.get("llm_model", "gpt-4")
            temperature = float(agent_settings.get("temperature", "0.7"))
            max_tokens = int(agent_settings.get("max_tokens", "2048"))
            system_prompt = agent_settings.get("system_prompt", "")
            
            # Get tenant and knowledge base info
            tenant_id = agent_config.get("tenant_id") or agent.get("tenant_id")
            knowledge_base_ids = []
            if "knowledge_bases" in agent_config:
                knowledge_base_ids = [kb.get("id") for kb in agent_config["knowledge_bases"] if kb.get("id")]
            
            # Yield start event
            yield {
                "type": "start",
                "message_id": message_id,
                "model": llm_model,
                "provider": llm_provider
            }
            
            # Retrieve context from vector store
            contexts = []
            if tenant_id:
                contexts = await self.retrieve_context(
                    query=query,
                    tenant_id=str(tenant_id),
                    knowledge_base_ids=knowledge_base_ids,
                    top_k=5
                )
                
                if contexts:
                    yield {
                        "type": "context",
                        "message_id": message_id,
                        "sources": [{"source": c["source"], "score": c["score"]} for c in contexts]
                    }
            
            # Build system prompt with context
            full_system_prompt = self._build_system_prompt(
                system_prompt, contexts, agent_settings
            )
            
            # Build messages
            messages = [{"role": "system", "content": full_system_prompt}]
            
            # Add chat history
            if chat_history:
                for msg in chat_history[-10:]:  # Last 10 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Stream response based on provider
            full_response = ""
            
            if llm_provider == "openai":
                async for chunk in self.stream_chat_openai(
                    messages=messages,
                    model=llm_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    full_response += chunk
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "message_id": message_id
                    }
            
            elif llm_provider == "anthropic":
                async for chunk in self.stream_chat_anthropic(
                    messages=messages,
                    system_prompt=full_system_prompt,
                    model=llm_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    full_response += chunk
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "message_id": message_id
                    }
            
            else:
                # Fallback for unsupported providers
                full_response = f"Provider '{llm_provider}' is not supported. Please configure OpenAI or Anthropic."
                yield {
                    "type": "chunk",
                    "content": full_response,
                    "message_id": message_id
                }
            
            # Yield end event
            yield {
                "type": "end",
                "message_id": message_id,
                "full_response": full_response,
                "sources": [c["source"] for c in contexts] if contexts else []
            }
            
        except Exception as e:
            logger.error(f"Error in RAG chat: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "message_id": message_id
            }
    
    async def simple_chat(
        self,
        query: str,
        system_prompt: str = "You are a helpful AI assistant.",
        model: str = "gpt-4",
        provider: str = "openai"
    ) -> str:
        """Simple non-streaming chat for internal use."""
        if provider == "openai" and self.openai_client:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ]
            )
            return response.choices[0].message.content
        
        elif provider == "anthropic" and self.anthropic_client:
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": query}]
            )
            return response.content[0].text
        
        raise ValueError(f"Provider '{provider}' not available or not configured")


# Singleton instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
