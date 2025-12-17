"""Role and Permission models."""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Role(BaseModel):
    """Role model for RBAC."""
    __tablename__ = "roles"

    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    guard_name = Column(String(255), default="api")
    description = Column(Text, nullable=True)
    type = Column(String(50), default="internal")  # internal or external
    is_system_generated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    permissions = relationship("Permission", secondary="role_has_permissions", back_populates="roles")
    users = relationship("User", secondary="model_has_roles", back_populates="roles")


class Permission(BaseModel):
    """Permission model for RBAC."""
    __tablename__ = "permissions"

    name = Column(String(255), nullable=False, unique=True)
    guard_name = Column(String(255), default="api")
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=True)
    app_module_id = Column(UUID(as_uuid=True), ForeignKey("app_modules.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    roles = relationship("Role", secondary="role_has_permissions", back_populates="permissions")
    users = relationship("User", secondary="model_has_permissions", back_populates="permissions")
    app_module = relationship("AppModule", back_populates="permissions")


class RoleHasPermission(BaseModel):
    """Association between roles and permissions."""
    __tablename__ = "role_has_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)


class ModelHasRole(BaseModel):
    """Association between models (users) and roles."""
    __tablename__ = "model_has_roles"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    model_type = Column(String(255), default="App\\Models\\User")
    model_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class ModelHasPermission(BaseModel):
    """Direct permission assignment to models (users)."""
    __tablename__ = "model_has_permissions"

    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)
    model_type = Column(String(255), default="App\\Models\\User")
    model_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
