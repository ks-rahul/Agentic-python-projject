"""Role and Permission schemas."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    module: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: UUID
    guard_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    permissions: List[PermissionResponse]
    total: int


class ModuleWisePermissionResponse(BaseModel):
    module: str
    permissions: List[PermissionResponse]


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: UUID
    guard_name: str
    is_active: bool
    permissions: Optional[List[PermissionResponse]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    roles: List[RoleResponse]
    total: int


class AttachPermissionsToRoleRequest(BaseModel):
    role_id: UUID
    permission_ids: List[UUID]


class DetachPermissionsFromRoleRequest(BaseModel):
    role_id: UUID
    permission_ids: List[UUID]


class AttachRolesToUserRequest(BaseModel):
    user_id: UUID
    role_ids: List[UUID]


class DetachRolesFromUserRequest(BaseModel):
    user_id: UUID
    role_ids: List[UUID]


class AttachPermissionsToUserRequest(BaseModel):
    user_id: UUID
    permission_ids: List[UUID]


class DetachPermissionsFromUserRequest(BaseModel):
    user_id: UUID
    permission_ids: List[UUID]
