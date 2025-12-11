"""Knowledge Base service."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge_base import KnowledgeBase
from app.services.base_service import BaseService


class KnowledgeBaseService(BaseService[KnowledgeBase]):
    """Service for knowledge base operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, KnowledgeBase)
    
    async def list_by_tenant(self, tenant_id: str) -> List[KnowledgeBase]:
        """List all knowledge bases for a tenant."""
        query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .where(KnowledgeBase.deleted_at.is_(None))
            .options(selectinload(KnowledgeBase.documents))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def list_trained(self, tenant_id: str) -> List[KnowledgeBase]:
        """List trained knowledge bases for a tenant."""
        query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .where(KnowledgeBase.deleted_at.is_(None))
            .where(KnowledgeBase.training_status == "trained")
        )
        result = await self.db.execute(query)
        return result.scalars().all()
