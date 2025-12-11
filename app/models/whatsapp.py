"""WhatsApp integration models."""
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, SoftDeleteMixin


class ConnectedWhatsappAccount(BaseModel, SoftDeleteMixin):
    """Connected WhatsApp Business Account."""
    __tablename__ = "connected_whatsapp_accounts"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # WhatsApp Business API credentials
    phone_number_id = Column(String(255), nullable=False, unique=True)
    waba_id = Column(String(255), nullable=True)  # WhatsApp Business Account ID
    access_token = Column(Text, nullable=True)
    
    # Display info
    phone_number = Column(String(50), nullable=True)
    display_phone_number = Column(String(50), nullable=True)
    verified_name = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Configuration
    config = Column(JSON, nullable=True)
