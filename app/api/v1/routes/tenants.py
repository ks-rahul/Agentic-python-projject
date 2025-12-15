"""Tenant management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.tenant import TenantResponse, TenantListResponse
from app.services.tenant_service import TenantService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/list", response_model=TenantListResponse)
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all tenants for current user."""
    tenant_service = TenantService(db)
    tenants = await tenant_service.get_user_tenants(current_user["user_id"])
    
    return TenantListResponse(
        tenants=tenants,
        total=len(tenants)
    )


@router.get("/get/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant details by ID."""
    tenant_service = TenantService(db)
    tenant = await tenant_service.get_by_id(str(tenant_id))
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return tenant
