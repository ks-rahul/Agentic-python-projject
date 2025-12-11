"""Tenant model for multi-tenancy."""
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Tenant(BaseModel, SoftDeleteMixin):
    """Tenant model for multi-tenant architecture."""
    __tablename__ = "tenants"

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    company_email = Column(String(255), nullable=True)
    company_phone = Column(String(50), nullable=True)
    profile_image = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    domain = Column(String(255), nullable=True)
    company_registration_number = Column(String(100), nullable=True)
    gst_vat_number = Column(String(100), nullable=True)
    status = Column(Enum(TenantStatus), default=TenantStatus.ACTIVE)
    max_users = Column(Integer, default=5)
    country_code = Column(String(10), nullable=True)
    timezone = Column(String(50), nullable=True)
    subscription_plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE)

    # Relationships
    users = relationship("User", secondary="tenant_users", back_populates="tenants")
    agents = relationship("Agent", back_populates="tenant")


class TenantUser(BaseModel):
    """Association table for tenant-user relationship."""
    __tablename__ = "tenant_users"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
