"""Agent service for agent management."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, AgentSetting, AgentKnowledgeBase
from app.services.base_service import BaseService


class AgentService(BaseService[Agent]):
    """Service for agent operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Agent)
    
    async def list_agents(self, tenant_id: Optional[str] = None) -> List[Agent]:
        """List all agents for a tenant."""
        query = (
            select(Agent)
            .where(Agent.deleted_at.is_(None))
            .options(selectinload(Agent.settings))
        )
        
        if tenant_id:
            query = query.where(Agent.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, id: str) -> Optional[Agent]:
        """Get agent by ID with relations."""
        query = (
            select(Agent)
            .where(Agent.id == id)
            .options(
                selectinload(Agent.settings),
                selectinload(Agent.knowledge_bases),
                selectinload(Agent.assistants),
                selectinload(Agent.intent_configurations)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create(
        self,
        name: str,
        tenant_id: Optional[str] = None,
        display_name: Optional[str] = None,
        type: str = "chatbot",
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Create a new agent with optional settings."""
        agent = await super().create(
            name=name,
            tenant_id=tenant_id,
            display_name=display_name or name,
            type=type,
            description=description
        )
        
        # Create settings if provided
        if settings:
            agent_setting = AgentSetting(
                agent_id=agent.id,
                **settings
            )
            self.db.add(agent_setting)
            await self.db.commit()
        
        return await self.get_by_id(str(agent.id))
    
    async def configure_settings(self, agent_id: str, settings: Dict[str, Any]) -> AgentSetting:
        """Configure or update agent settings."""
        # Check if settings exist
        query = select(AgentSetting).where(AgentSetting.agent_id == agent_id)
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing settings
            for key, value in settings.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.db.commit()
            return existing
        else:
            # Create new settings
            agent_setting = AgentSetting(agent_id=agent_id, **settings)
            self.db.add(agent_setting)
            await self.db.commit()
            return agent_setting
    
    async def attach_knowledge_base(self, agent_id: str, knowledge_base_id: str) -> None:
        """Attach a knowledge base to an agent."""
        # Check if already attached
        query = select(AgentKnowledgeBase).where(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.knowledge_base_id == knowledge_base_id
        )
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            return  # Already attached
        
        akb = AgentKnowledgeBase(
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id
        )
        self.db.add(akb)
        await self.db.commit()
    
    async def detach_knowledge_base(self, agent_id: str, knowledge_base_id: str) -> None:
        """Detach a knowledge base from an agent."""
        query = select(AgentKnowledgeBase).where(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.knowledge_base_id == knowledge_base_id
        )
        result = await self.db.execute(query)
        akb = result.scalar_one_or_none()
        
        if akb:
            await self.db.delete(akb)
            await self.db.commit()
    
    async def get_full_configuration(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full agent configuration for chat widget."""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        return {
            "agent": agent,
            "knowledge_bases": [
                {"id": str(akb.knowledge_base_id)} 
                for akb in agent.knowledge_bases
            ],
            "assistants": [
                {"id": str(a.id), "name": a.name} 
                for a in agent.assistants
            ],
            "intent_configurations": [
                {
                    "id": str(ic.id),
                    "intent_name": ic.intent_name,
                    "trigger_phrases": ic.trigger_phrases
                }
                for ic in agent.intent_configurations
            ]
        }
