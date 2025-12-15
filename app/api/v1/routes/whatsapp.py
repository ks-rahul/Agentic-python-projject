"""WhatsApp Business API integration routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db.mysql import get_db
from app.services.whatsapp_service import WhatsAppService
from app.core.security import get_current_user

router = APIRouter()


class WhatsAppCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class WhatsAppConfigurationRequest(BaseModel):
    agent_id: UUID
    tenant_id: UUID


@router.get("/signup-url")
async def get_signup_url(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get WhatsApp Business signup URL."""
    whatsapp_service = WhatsAppService(db)
    url = await whatsapp_service.get_signup_url(current_user.get("tenant_id"))
    return {"signup_url": url}


@router.post("/callback")
async def handle_callback(
    request: WhatsAppCallbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Handle WhatsApp OAuth callback."""
    whatsapp_service = WhatsAppService(db)
    result = await whatsapp_service.handle_callback(
        code=request.code,
        state=request.state,
        tenant_id=current_user.get("tenant_id")
    )
    return result


@router.post("/configuration")
async def get_configuration(
    request: WhatsAppConfigurationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get WhatsApp configuration for agent."""
    whatsapp_service = WhatsAppService(db)
    config = await whatsapp_service.get_configuration(
        str(request.agent_id),
        str(request.tenant_id)
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp configuration not found"
        )
    
    return config


@router.get("/configuration/{phone_number_id}")
async def get_configuration_by_phone_number(
    phone_number_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get WhatsApp configuration by phone number ID (public endpoint)."""
    whatsapp_service = WhatsAppService(db)
    config = await whatsapp_service.get_configuration_by_phone_number(phone_number_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp configuration not found"
        )
    
    return config


@router.get("/test-connection/{agent_id}/{tenant_id}")
async def test_connection(
    agent_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Test WhatsApp connection."""
    whatsapp_service = WhatsAppService(db)
    result = await whatsapp_service.test_connection(str(agent_id), str(tenant_id))
    return result


@router.delete("/disconnect/{agent_id}/{tenant_id}")
async def disconnect_account(
    agent_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Disconnect WhatsApp account."""
    whatsapp_service = WhatsAppService(db)
    await whatsapp_service.disconnect(str(agent_id), str(tenant_id))
    return {"message": "WhatsApp account disconnected successfully"}


@router.get("/verify-setup")
async def verify_setup(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Verify WhatsApp setup configuration."""
    whatsapp_service = WhatsAppService(db)
    result = await whatsapp_service.verify_setup(current_user.get("tenant_id"))
    return result
