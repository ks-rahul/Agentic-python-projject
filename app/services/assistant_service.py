"""Assistant service."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assistant import Assistant, AssistantConfiguration, AssistantIntentConfiguration
from app.models.agent import AgentAssistant
from app.services.base_service import BaseService


class AssistantService(BaseService[Assistant]):
    """Service for assistant operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Assistant)
    
    async def list_assistants(self, tenant_id: str) -> List[Assistant]:
        """List assistants for a tenant."""
        query = (
            select(Assistant)
            .where(Assistant.tenant_id == tenant_id)
            .where(Assistant.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def save_configurations(self, assistant_id: str, configurations: List) -> None:
        """Save assistant configurations."""
        # Remove existing configurations
        await self.db.execute(
            delete(AssistantConfiguration).where(AssistantConfiguration.assistant_id == assistant_id)
        )
        
        # Add new configurations
        for config in configurations:
            ac = AssistantConfiguration(
                assistant_id=assistant_id,
                **config.model_dump()
            )
            self.db.add(ac)
        
        await self.db.commit()
    
    async def attach_to_agent(
        self,
        agent_id: str,
        assistant_id: str,
        required_tenant_auth: Optional[str] = None,
        auth_configurations: Optional[Dict] = None
    ) -> None:
        """Attach assistant to agent."""
        existing = await self.db.execute(
            select(AgentAssistant).where(
                AgentAssistant.agent_id == agent_id,
                AgentAssistant.assistant_id == assistant_id
            )
        )
        if existing.scalar_one_or_none():
            return
        
        aa = AgentAssistant(
            agent_id=agent_id,
            assistant_id=assistant_id,
            required_tenant_auth=required_tenant_auth,
            auth_configurations=auth_configurations
        )
        self.db.add(aa)
        await self.db.commit()
    
    async def detach_from_agent(self, agent_id: str, assistant_id: str) -> None:
        """Detach assistant from agent."""
        await self.db.execute(
            delete(AgentAssistant).where(
                AgentAssistant.agent_id == agent_id,
                AgentAssistant.assistant_id == assistant_id
            )
        )
        await self.db.commit()
    
    async def update_agent_assistant_auth(
        self,
        agent_id: str,
        assistant_id: str,
        auth_credentials: Dict
    ) -> None:
        """Update agent assistant auth credentials."""
        query = select(AgentAssistant).where(
            AgentAssistant.agent_id == agent_id,
            AgentAssistant.assistant_id == assistant_id
        )
        result = await self.db.execute(query)
        aa = result.scalar_one_or_none()
        
        if aa:
            aa.auth_credentials = auth_credentials
            await self.db.commit()
    
    async def get_agent_assistants(self, agent_id: str) -> List[Dict]:
        """Get assistants for an agent."""
        query = (
            select(AgentAssistant)
            .where(AgentAssistant.agent_id == agent_id)
            .options(selectinload(AgentAssistant.assistant))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def generate_code(self, assistant_id: str, prompt: Optional[str] = None) -> Dict:
        """Generate code for assistant."""
        # TODO: Implement code generation with LLM
        return {"message": "Code generation not implemented", "code": ""}
    
    async def invoke_method(
        self,
        assistant_id: str,
        method_name: str,
        parameters: Optional[Dict] = None
    ) -> Dict:
        """Invoke assistant method in playground."""
        # TODO: Implement method invocation
        return {"message": "Method invocation not implemented", "result": None}
    
    async def deploy(self, assistant_id: str, deployment_config: Optional[Dict] = None) -> Dict:
        """Deploy assistant."""
        await self.update(assistant_id, status="deployed")
        return {"message": "Assistant deployed", "assistant_id": assistant_id}
    
    # Intent Configuration methods
    async def list_intent_configurations(self, tenant_id: str) -> List[AssistantIntentConfiguration]:
        """List intent configurations for a tenant."""
        query = (
            select(AssistantIntentConfiguration)
            .where(AssistantIntentConfiguration.tenant_id == tenant_id)
            .where(AssistantIntentConfiguration.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_intent_configuration(self, config_id: str) -> Optional[AssistantIntentConfiguration]:
        """Get intent configuration by ID."""
        query = select(AssistantIntentConfiguration).where(AssistantIntentConfiguration.id == config_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_intent_configuration(self, data) -> AssistantIntentConfiguration:
        """Create intent configuration."""
        config = AssistantIntentConfiguration(**data.model_dump())
        self.db.add(config)
        await self.db.commit()
        return config
    
    async def update_intent_configuration(self, config_id: str, data) -> AssistantIntentConfiguration:
        """Update intent configuration."""
        config = await self.get_intent_configuration(config_id)
        if config:
            for key, value in data.model_dump(exclude_unset=True).items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
            await self.db.commit()
        return config
    
    async def delete_intent_configuration(self, config_id: str) -> None:
        """Delete intent configuration."""
        config = await self.get_intent_configuration(config_id)
        if config:
            from datetime import datetime
            config.deleted_at = datetime.utcnow()
            await self.db.commit()
    
    async def get_intent_configurations_by_agent(self, agent_id: str) -> List[AssistantIntentConfiguration]:
        """Get intent configurations by agent."""
        query = (
            select(AssistantIntentConfiguration)
            .where(AssistantIntentConfiguration.agent_id == agent_id)
            .where(AssistantIntentConfiguration.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # OAuth methods
    async def initialize_oauth(self, assistant_id: str) -> Dict:
        """Initialize OAuth flow."""
        # TODO: Implement OAuth initialization
        return {"message": "OAuth not implemented", "redirect_url": ""}
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict:
        """Handle OAuth callback."""
        # TODO: Implement OAuth callback handling
        return {"message": "OAuth callback not implemented"}
    
    async def refresh_oauth_token(self, assistant_id: str) -> Dict:
        """Refresh OAuth token."""
        # TODO: Implement token refresh
        return {"message": "Token refresh not implemented"}
    
    async def revoke_oauth_token(self, assistant_id: str) -> None:
        """Revoke OAuth token."""
        # TODO: Implement token revocation
        pass
