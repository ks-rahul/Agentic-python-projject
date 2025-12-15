"""Role and Permission management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse, PermissionListResponse, ModuleWisePermissionResponse,
    AttachPermissionsToRoleRequest, DetachPermissionsFromRoleRequest,
    AttachRolesToUserRequest, DetachRolesFromUserRequest,
    AttachPermissionsToUserRequest, DetachPermissionsFromUserRequest
)
from app.services.role_service import RoleService
from app.core.security import get_current_user

router = APIRouter()
permission_router = APIRouter()


# Role routes
@router.get("/list", response_model=RoleListResponse)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all roles."""
    role_service = RoleService(db)
    roles = await role_service.list_roles()
    
    return RoleListResponse(
        roles=roles,
        total=len(roles)
    )


@router.post("/create", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new role."""
    role_service = RoleService(db)
    role = await role_service.create_role(
        name=request.name,
        description=request.description,
        user_id=current_user["user_id"]
    )
    return role


@router.get("/get/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get role by ID."""
    role_service = RoleService(db)
    role = await role_service.get_role(str(role_id))
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return role


@router.put("/update/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update role."""
    role_service = RoleService(db)
    
    role = await role_service.get_role(str(role_id))
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    updated_role = await role_service.update_role(
        str(role_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_role


@router.delete("/delete/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete role."""
    role_service = RoleService(db)
    
    role = await role_service.get_role(str(role_id))
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    await role_service.delete_role(str(role_id))
    return None


@router.patch("/toggle-status/{role_id}")
async def toggle_role_status(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Toggle role active status."""
    role_service = RoleService(db)
    
    role = await role_service.get_role(str(role_id))
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    new_status = not role.is_active
    await role_service.update_role(str(role_id), is_active=new_status)
    
    return {"message": f"Role status changed to {'active' if new_status else 'inactive'}"}


@router.post("/attach-to-user")
async def attach_roles_to_user(
    request: AttachRolesToUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Attach roles to user."""
    role_service = RoleService(db)
    await role_service.attach_roles_to_user(
        str(request.user_id),
        [str(rid) for rid in request.role_ids]
    )
    return {"message": "Roles attached successfully"}


@router.post("/detach-from-user")
async def detach_roles_from_user(
    request: DetachRolesFromUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detach roles from user."""
    role_service = RoleService(db)
    await role_service.detach_roles_from_user(
        str(request.user_id),
        [str(rid) for rid in request.role_ids]
    )
    return {"message": "Roles detached successfully"}


# Permission routes
@permission_router.get("/list", response_model=PermissionListResponse)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all permissions."""
    role_service = RoleService(db)
    permissions = await role_service.list_permissions()
    
    return PermissionListResponse(
        permissions=permissions,
        total=len(permissions)
    )


@permission_router.get("/module-wise/list")
async def list_permissions_module_wise(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List permissions grouped by module."""
    role_service = RoleService(db)
    permissions = await role_service.list_permissions_by_module()
    return permissions


@permission_router.get("/get/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get permission by ID."""
    role_service = RoleService(db)
    permission = await role_service.get_permission(str(permission_id))
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    return permission


@permission_router.get("/get/module-wise/{user_id}")
async def get_user_permissions_module_wise(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user permissions grouped by module."""
    role_service = RoleService(db)
    permissions = await role_service.get_user_permissions_by_module(str(user_id))
    return permissions


@permission_router.post("/attach-to-role")
async def attach_permissions_to_role(
    request: AttachPermissionsToRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Attach permissions to role."""
    role_service = RoleService(db)
    await role_service.attach_permissions_to_role(
        str(request.role_id),
        [str(pid) for pid in request.permission_ids]
    )
    return {"message": "Permissions attached successfully"}


@permission_router.post("/detach-from-role")
async def detach_permissions_from_role(
    request: DetachPermissionsFromRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detach permissions from role."""
    role_service = RoleService(db)
    await role_service.detach_permissions_from_role(
        str(request.role_id),
        [str(pid) for pid in request.permission_ids]
    )
    return {"message": "Permissions detached successfully"}


@permission_router.post("/attach-to-user")
async def attach_permissions_to_user(
    request: AttachPermissionsToUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Attach permissions directly to user."""
    role_service = RoleService(db)
    await role_service.attach_permissions_to_user(
        str(request.user_id),
        [str(pid) for pid in request.permission_ids]
    )
    return {"message": "Permissions attached successfully"}


@permission_router.post("/detach-from-user")
async def detach_permissions_from_user(
    request: DetachPermissionsFromUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detach permissions from user."""
    role_service = RoleService(db)
    await role_service.detach_permissions_from_user(
        str(request.user_id),
        [str(pid) for pid in request.permission_ids]
    )
    return {"message": "Permissions detached successfully"}
