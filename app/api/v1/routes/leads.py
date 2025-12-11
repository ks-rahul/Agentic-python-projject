"""Lead management routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.schemas.lead import (
    LeadFormCreate, LeadFormUpdate, LeadFormResponse, LeadFormListResponse,
    LeadCreate, LeadResponse, LeadListResponse, PublicLeadCreate
)
from app.services.lead_service import LeadService
from app.core.security import get_current_user

router = APIRouter()
public_router = APIRouter()


# Lead Form routes
@router.get("/list", response_model=LeadFormListResponse)
async def list_lead_forms(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all lead forms."""
    lead_service = LeadService(db)
    forms = await lead_service.list_lead_forms(current_user.get("tenant_id"))
    
    return LeadFormListResponse(
        lead_forms=forms,
        total=len(forms)
    )


@router.post("/create-or-update", response_model=LeadFormResponse)
async def create_or_update_lead_form(
    request: LeadFormCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create or update lead form."""
    lead_service = LeadService(db)
    form = await lead_service.create_or_update_lead_form(request)
    return form


@router.get("/by-agent/{agent_id}", response_model=LeadListResponse)
async def get_leads_by_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get leads by agent ID."""
    lead_service = LeadService(db)
    leads = await lead_service.get_leads_by_agent(str(agent_id))
    
    return LeadListResponse(
        leads=leads,
        total=len(leads)
    )


@router.get("/by-tenant/{tenant_id}", response_model=LeadListResponse)
async def get_leads_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get leads by tenant ID."""
    lead_service = LeadService(db)
    leads = await lead_service.get_leads_by_tenant(str(tenant_id))
    
    return LeadListResponse(
        leads=leads,
        total=len(leads)
    )


@router.get("/form-by-tenant/{tenant_id}", response_model=LeadFormResponse)
async def get_lead_form_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get lead form by tenant ID."""
    lead_service = LeadService(db)
    form = await lead_service.get_lead_form_by_tenant(str(tenant_id))
    
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead form not found"
        )
    
    return form


@router.get("/leads-by-form/{form_id}", response_model=LeadListResponse)
async def get_leads_by_form(
    form_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get leads by form ID."""
    lead_service = LeadService(db)
    leads = await lead_service.get_leads_by_form(str(form_id))
    
    return LeadListResponse(
        leads=leads,
        total=len(leads)
    )


# Public routes (no auth required)
@public_router.post("/leads/save", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def save_lead(
    request: PublicLeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """Save a lead (public endpoint)."""
    lead_service = LeadService(db)
    lead = await lead_service.create_lead(request)
    return lead
