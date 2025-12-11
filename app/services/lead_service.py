"""Lead service."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadForm
from app.services.base_service import BaseService


class LeadService(BaseService[Lead]):
    """Service for lead operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Lead)
    
    async def list_lead_forms(self, tenant_id: str) -> List[LeadForm]:
        """List lead forms for a tenant."""
        query = (
            select(LeadForm)
            .where(LeadForm.tenant_id == tenant_id)
            .where(LeadForm.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_or_update_lead_form(self, data) -> LeadForm:
        """Create or update lead form."""
        query = select(LeadForm).where(
            LeadForm.tenant_id == str(data.tenant_id),
            LeadForm.agent_id == str(data.agent_id)
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            for key, value in data.model_dump(exclude_unset=True).items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            await self.db.commit()
            return existing
        else:
            form = LeadForm(**data.model_dump())
            self.db.add(form)
            await self.db.commit()
            return form
    
    async def get_leads_by_agent(self, agent_id: str) -> List[Lead]:
        """Get leads by agent."""
        query = (
            select(Lead)
            .where(Lead.agent_id == agent_id)
            .where(Lead.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_leads_by_tenant(self, tenant_id: str) -> List[Lead]:
        """Get leads by tenant."""
        query = (
            select(Lead)
            .where(Lead.tenant_id == tenant_id)
            .where(Lead.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_lead_form_by_tenant(self, tenant_id: str) -> Optional[LeadForm]:
        """Get lead form by tenant."""
        query = (
            select(LeadForm)
            .where(LeadForm.tenant_id == tenant_id)
            .where(LeadForm.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_leads_by_form(self, form_id: str) -> List[Lead]:
        """Get leads by form."""
        query = (
            select(Lead)
            .where(Lead.lead_form_id == form_id)
            .where(Lead.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_lead(self, data) -> Lead:
        """Create a new lead."""
        lead = Lead(**data.model_dump())
        self.db.add(lead)
        await self.db.commit()
        return lead
