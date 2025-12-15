"""Tenant service for tenant management."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant import Tenant, TenantUser
from app.services.base_service import BaseService

class TenantService(BaseService[Tenant]):
    """Service for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Tenant)
    
    async def get_user_tenants(self, user_id: str) -> List[Tenant]:
        """Get all tenants for a user."""
        query = (
            select(Tenant)
            .join(TenantUser)
            .where(TenantUser.user_id == user_id)
            .where(Tenant.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_with_user(
        self,
        user_id: str,
        name: str,
        **kwargs
    ) -> Tenant:
        """Create a tenant and associate with user."""
        tenant = await self.create(
            created_by=user_id,
            name=f"{name}'s Workspace",
            **kwargs
        )
        
        # Associate user with tenant
        tenant_user = TenantUser(tenant_id=tenant.id, user_id=user_id)
        self.db.add(tenant_user)
        await self.db.commit()
        
        return tenant
