"""Lead and Lead Form models."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class LeadForm(BaseModel, SoftDeleteMixin):
    """Lead form configuration."""
    __tablename__ = "lead_forms"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Form fields configuration
    fields = Column(JSON, nullable=True)
    
    # Behavior
    is_active = Column(Boolean, default=True)
    show_after_messages = Column(String(10), default="3")
    trigger_condition = Column(String(100), nullable=True)
    
    # Styling
    title = Column(String(255), default="Get in touch")
    submit_button_text = Column(String(100), default="Submit")
    success_message = Column(Text, default="Thank you for your submission!")

    # Relationships
    agent = relationship("Agent", back_populates="lead_form")
    leads = relationship("Lead", back_populates="lead_form")


class Lead(BaseModel, SoftDeleteMixin):
    """Lead submission."""
    __tablename__ = "leads"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    lead_form_id = Column(UUID(as_uuid=True), ForeignKey("lead_forms.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Lead data
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    
    # Additional form data
    form_data = Column(JSON, nullable=True)
    
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    source = Column(String(100), default="chatbot")
    
    # Metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    lead_form = relationship("LeadForm", back_populates="leads")
