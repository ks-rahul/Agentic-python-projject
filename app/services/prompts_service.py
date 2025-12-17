"""Prompts service for code generation and AI interactions."""
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


def read_code_file(file_path: str) -> str:
    """Read a code file and return its contents."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def prompt_code(
    query: str,
    payload: Dict[str, Any],
    endpoints: Dict[str, Any],
    configurations: Dict[str, Any],
    base_url: str,
    fields_mapping: Dict[str, Any],
    action_name: str,
    auth_header_code: str = "",
) -> str:
    """Generate prompt for code generation."""
    return f"""
    ## Role:
    You are a helpful AI assistant. You only provide Python code and nothing else.
    Do not wrap code inside markdown blocks. Just output clean, runnable Python code.

    ## Imports:
    Always include:
    - import requests
    - from app.services.auth import get_auth_headers
    - from app.core.logging import get_logger
    - logger = get_logger(__name__)

    ## Context:
    - Use `requests` for HTTP calls.
    - Each generated function must:
        1. Use `get_auth_headers(payload)` for authentication headers.
        2. Merge additional `custom_headers` if present in payload.
        3. Dynamically construct path, query, body, headers → no hardcoding.
        4. Filter out reserved keys (`auth_type`, tokens, access_token, refresh_token, credentials, etc.) from query params.
        5. Return structured JSON: 
            {{ "data": ..., "status": "success" }} 
          or 
            {{ "error": ..., "details": ... }}
        6. Catch all exceptions and return inside dict (never raise).
    

    ## Rules:
    - Function name must exactly match the action name from endpoints → {endpoints}, if there are multiple action id, create multiple functions.
    - Base URL should be → {base_url}.
    - Query params come from payload (dict or list). Reserved keys must not leak into query.
    - Response errors must be handled gracefully.
    - There will be as many functions as many their are action_name in endpoints, action_name: {action_name}, endpoints: {endpoints}

    ## Inputs:
    - User Query: {query}
    - Payload: {payload}
    - Endpoints: {endpoints}
    - Configurations: {configurations}
    - Base URL: {base_url}
    - Fields Mapping: {fields_mapping}
    - Action name: {action_name}, All the names under actions, will be functions

    ## Auth Helper:
    {auth_header_code}

    ## Output:
    - Valid Python code
    - Start with `import requests`
    - Functions signatures: def Action Name(payload): ...
    - Must log query params + headers
    - Must use black-compatible indentation
    """


def role_and_persona(
    name: str,
    tone: str,
    persona_description: str,
    role: str,
    languages: str,
) -> str:
    """Generate role and persona prompt section."""
    return f"""#Role and Persona:           

    "Your name is {name}, tell only this name when asked, {name}, "
    "your tone must be {tone}, "
    "your persona is {persona_description}, "
    "your role is {role}, "
    "language is {languages},
    Always reason internally. Do not include reasoning, only respond with the final answer.
"""


def rules_for_response() -> str:
    """Generate rules for AI response."""
    return """
    ## Rules for Response:
    - Never break character.
    - Do not answer beyond your defined role and persona.
    - Do not answer questions outside your expertise.
    - Always maintain the specified tone.
    - Do not answer anything except knowledge base, politely refuse and move them towards knowledge base. Call knowledge_base_retriever to find what is your data about.
    - Do not answer about anything such as about donald trump or any popular figure, unless specified in knowledge base. Call knowledge_base_retriever to find what is your data about.
    - Do not reveal you are an AI model.
    - Always reason internally. Do not include reasoning, only respond with the final answer.
    - Always know that you are here for a specified role and purpose.
    - If information may exist in the knowledge base (policies/reports/user manuals), ALWAYS call knowledge_base_retriever.
    - If the question is outside the knowledge base, answer normally using the LLM.
    """


def system_prompt_for_agent(
    agent_name: str,
    agent_description: str,
    tone: str = "professional",
    persona: str = "helpful assistant",
    role: str = "customer support",
    languages: str = "English",
    custom_instructions: Optional[str] = None,
) -> str:
    """Generate complete system prompt for an agent."""
    base_prompt = f"""You are {agent_name}, {agent_description}.

{role_and_persona(agent_name, tone, persona, role, languages)}

{rules_for_response()}
"""
    if custom_instructions:
        base_prompt += f"\n## Additional Instructions:\n{custom_instructions}\n"

    return base_prompt


def rag_system_prompt(
    agent_name: str,
    context: str,
    tone: str = "professional",
) -> str:
    """Generate system prompt for RAG-based responses."""
    return f"""You are {agent_name}, a helpful AI assistant.

## Context from Knowledge Base:
{context}

## Instructions:
- Answer the user's question based ONLY on the provided context.
- If the context doesn't contain relevant information, say "I don't have information about that in my knowledge base."
- Maintain a {tone} tone throughout.
- Be concise and accurate.
- Do not make up information not present in the context.
- If asked about topics outside the context, politely redirect to what you can help with.
"""


def code_generation_system_prompt() -> str:
    """System prompt for code generation tasks."""
    return """You are an expert Python code generator.

## Rules:
1. Generate clean, production-ready Python code
2. Include proper error handling
3. Add type hints where appropriate
4. Include docstrings for functions and classes
5. Follow PEP 8 style guidelines
6. Use async/await for I/O operations when appropriate
7. Never include markdown code blocks - output raw Python code only
8. Include necessary imports at the top
9. Handle edge cases gracefully
"""


def intent_classification_prompt(intents: list[Dict[str, Any]]) -> str:
    """Generate prompt for intent classification."""
    intent_descriptions = "\n".join(
        [f"- {intent['name']}: {intent.get('description', '')}" for intent in intents]
    )
    return f"""Classify the user's message into one of the following intents:

{intent_descriptions}

Respond with ONLY the intent name, nothing else.
If the message doesn't match any intent, respond with "unknown".
"""


def summarization_prompt(max_length: int = 200) -> str:
    """Generate prompt for text summarization."""
    return f"""Summarize the following text in {max_length} words or less.
Focus on the key points and main ideas.
Be concise and accurate.
"""


class PromptsService:
    """Service for managing and generating prompts."""

    def __init__(self):
        self._prompt_cache: Dict[str, str] = {}

    def get_agent_system_prompt(
        self,
        agent_config: Dict[str, Any],
        custom_instructions: Optional[str] = None,
    ) -> str:
        """Generate system prompt from agent configuration."""
        return system_prompt_for_agent(
            agent_name=agent_config.get("name", "Assistant"),
            agent_description=agent_config.get("description", "a helpful AI assistant"),
            tone=agent_config.get("tone", "professional"),
            persona=agent_config.get("persona", "helpful assistant"),
            role=agent_config.get("role", "customer support"),
            languages=agent_config.get("languages", "English"),
            custom_instructions=custom_instructions,
        )

    def get_rag_prompt(
        self,
        agent_name: str,
        context: str,
        tone: str = "professional",
    ) -> str:
        """Generate RAG system prompt."""
        return rag_system_prompt(agent_name, context, tone)

    def get_code_generation_prompt(self) -> str:
        """Get code generation system prompt."""
        return code_generation_system_prompt()

    def get_intent_prompt(self, intents: list[Dict[str, Any]]) -> str:
        """Get intent classification prompt."""
        return intent_classification_prompt(intents)


def get_prompts_service() -> PromptsService:
    """Get prompts service instance."""
    return PromptsService()
