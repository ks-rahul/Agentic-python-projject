"""Chat Builder service."""
from typing import Optional, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat_builder import ChatBuilder, ChatBuilderAgent
from app.services.base_service import BaseService


class ChatBuilderService(BaseService[ChatBuilder]):
    """Service for chat builder operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatBuilder)
    
    async def list_by_tenant(self, tenant_id: str) -> List[ChatBuilder]:
        """List chat builders for a tenant."""
        query = (
            select(ChatBuilder)
            .where(ChatBuilder.tenant_id == tenant_id)
            .where(ChatBuilder.deleted_at.is_(None))
            .options(selectinload(ChatBuilder.agents))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def configure_agents(self, chat_builder_id: str, agent_ids: List[str]) -> None:
        """Configure agents for a chat builder."""
        # Remove existing associations
        await self.db.execute(
            delete(ChatBuilderAgent).where(ChatBuilderAgent.chat_builder_id == chat_builder_id)
        )
        
        # Add new associations
        for agent_id in agent_ids:
            cba = ChatBuilderAgent(
                chat_builder_id=chat_builder_id,
                agent_id=agent_id
            )
            self.db.add(cba)
        
        await self.db.commit()
