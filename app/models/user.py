"""User model."""
from sqlalchemy import Column, String, DateTime, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(BaseModel, SoftDeleteMixin):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    profile_image = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    country_code = Column(String(10), nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Social auth fields
    provider = Column(String(50), nullable=True)
    provider_id = Column(String(255), nullable=True)
    provider_token = Column(Text, nullable=True)
    provider_refresh_token = Column(Text, nullable=True)
    
    remember_token = Column(String(100), nullable=True)

    # Relationships
    tenants = relationship("Tenant", secondary="tenant_users", back_populates="users")
    roles = relationship("Role", secondary="model_has_roles", back_populates="users")
    permissions = relationship("Permission", secondary="model_has_permissions", back_populates="users")
