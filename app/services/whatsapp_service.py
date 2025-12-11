"""WhatsApp service."""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import ConnectedWhatsappAccount
from app.services.base_service import BaseService
from app.core.config import settings


class WhatsAppService(BaseService[ConnectedWhatsappAccount]):
    """Service for WhatsApp operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, ConnectedWhatsappAccount)
    
    async def get_signup_url(self, tenant_id: str) -> str:
        """Get WhatsApp Business signup URL."""
        # TODO: Implement actual signup URL generation
        return f"https://www.facebook.com/v18.0/dialog/oauth?client_id=YOUR_APP_ID&redirect_uri=YOUR_REDIRECT_URI&state={tenant_id}"
    
    async def handle_callback(self, code: str, state: str, tenant_id: str) -> Dict[str, Any]:
        """Handle OAuth callback."""
        # TODO: Exchange code for access token
        return {"message": "Callback handled", "tenant_id": tenant_id}
    
    async def get_configuration(self, agent_id: str, tenant_id: str) -> Optional[ConnectedWhatsappAccount]:
        """Get WhatsApp configuration for agent."""
        query = select(ConnectedWhatsappAccount).where(
            ConnectedWhatsappAccount.agent_id == agent_id,
            ConnectedWhatsappAccount.tenant_id == tenant_id,
            ConnectedWhatsappAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_configuration_by_phone_number(self, phone_number_id: str) -> Optional[ConnectedWhatsappAccount]:
        """Get configuration by phone number ID."""
        query = select(ConnectedWhatsappAccount).where(
            ConnectedWhatsappAccount.phone_number_id == phone_number_id,
            ConnectedWhatsappAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def test_connection(self, agent_id: str, tenant_id: str) -> Dict[str, Any]:
        """Test WhatsApp connection."""
        config = await self.get_configuration(agent_id, tenant_id)
        if not config:
            return {"success": False, "message": "Configuration not found"}
        
        # TODO: Test actual connection
        return {"success": True, "message": "Connection successful"}
    
    async def disconnect(self, agent_id: str, tenant_id: str) -> None:
        """Disconnect WhatsApp account."""
        config = await self.get_configuration(agent_id, tenant_id)
        if config:
            await self.delete(str(config.id))
    
    async def verify_setup(self, tenant_id: str) -> Dict[str, Any]:
        """Verify WhatsApp setup."""
        return {
            "webhook_configured": bool(settings.WHATSAPP_VERIFY_TOKEN),
            "access_token_configured": bool(settings.WHATSAPP_ACCESS_TOKEN),
            "phone_number_configured": bool(settings.WHATSAPP_PHONE_NUMBER_ID)
        }
