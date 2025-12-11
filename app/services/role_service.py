"""Role and Permission service."""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role, Permission, RoleHasPermission, ModelHasRole, ModelHasPermission
from app.services.base_service import BaseService


class RoleService(BaseService[Role]):
    """Service for role and permission operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Role)
    
    async def list_roles(self) -> List[Role]:
        """List all roles."""
        query = select(Role).options(selectinload(Role.permissions))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID with permissions."""
        query = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_role(self, name: str, description: str = None, user_id: str = None) -> Role:
        """Create a new role."""
        role = Role(name=name, description=description, user_id=user_id)
        self.db.add(role)
        await self.db.commit()
        return role
    
    async def update_role(self, role_id: str, **kwargs) -> Role:
        """Update a role."""
        return await self.update(role_id, **kwargs)
    
    async def delete_role(self, role_id: str) -> None:
        """Delete a role."""
        await self.hard_delete(role_id)
    
    async def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        query = select(Permission)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def list_permissions_by_module(self) -> List[Dict[str, Any]]:
        """List permissions grouped by module."""
        permissions = await self.list_permissions()
        
        modules = {}
        for perm in permissions:
            module = perm.module or "general"
            if module not in modules:
                modules[module] = []
            modules[module].append(perm)
        
        return [{"module": k, "permissions": v} for k, v in modules.items()]
    
    async def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID."""
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_permissions_by_module(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user permissions grouped by module."""
        # Get permissions from roles
        query = (
            select(Permission)
            .join(RoleHasPermission)
            .join(Role)
            .join(ModelHasRole)
            .where(ModelHasRole.model_id == user_id)
        )
        result = await self.db.execute(query)
        role_permissions = result.scalars().all()
        
        # Get direct permissions
        query = (
            select(Permission)
            .join(ModelHasPermission)
            .where(ModelHasPermission.model_id == user_id)
        )
        result = await self.db.execute(query)
        direct_permissions = result.scalars().all()
        
        # Combine and group by module
        all_permissions = list(set(role_permissions + direct_permissions))
        
        modules = {}
        for perm in all_permissions:
            module = perm.module or "general"
            if module not in modules:
                modules[module] = []
            modules[module].append(perm)
        
        return [{"module": k, "permissions": v} for k, v in modules.items()]
    
    async def attach_permissions_to_role(self, role_id: str, permission_ids: List[str]) -> None:
        """Attach permissions to a role."""
        for perm_id in permission_ids:
            existing = await self.db.execute(
                select(RoleHasPermission).where(
                    RoleHasPermission.role_id == role_id,
                    RoleHasPermission.permission_id == perm_id
                )
            )
            if not existing.scalar_one_or_none():
                rhp = RoleHasPermission(role_id=role_id, permission_id=perm_id)
                self.db.add(rhp)
        await self.db.commit()
    
    async def detach_permissions_from_role(self, role_id: str, permission_ids: List[str]) -> None:
        """Detach permissions from a role."""
        await self.db.execute(
            delete(RoleHasPermission).where(
                RoleHasPermission.role_id == role_id,
                RoleHasPermission.permission_id.in_(permission_ids)
            )
        )
        await self.db.commit()
    
    async def attach_roles_to_user(self, user_id: str, role_ids: List[str]) -> None:
        """Attach roles to a user."""
        for role_id in role_ids:
            existing = await self.db.execute(
                select(ModelHasRole).where(
                    ModelHasRole.model_id == user_id,
                    ModelHasRole.role_id == role_id
                )
            )
            if not existing.scalar_one_or_none():
                mhr = ModelHasRole(model_id=user_id, role_id=role_id)
                self.db.add(mhr)
        await self.db.commit()
    
    async def detach_roles_from_user(self, user_id: str, role_ids: List[str]) -> None:
        """Detach roles from a user."""
        await self.db.execute(
            delete(ModelHasRole).where(
                ModelHasRole.model_id == user_id,
                ModelHasRole.role_id.in_(role_ids)
            )
        )
        await self.db.commit()
    
    async def attach_permissions_to_user(self, user_id: str, permission_ids: List[str]) -> None:
        """Attach permissions directly to a user."""
        for perm_id in permission_ids:
            existing = await self.db.execute(
                select(ModelHasPermission).where(
                    ModelHasPermission.model_id == user_id,
                    ModelHasPermission.permission_id == perm_id
                )
            )
            if not existing.scalar_one_or_none():
                mhp = ModelHasPermission(model_id=user_id, permission_id=perm_id)
                self.db.add(mhp)
        await self.db.commit()
    
    async def detach_permissions_from_user(self, user_id: str, permission_ids: List[str]) -> None:
        """Detach permissions from a user."""
        await self.db.execute(
            delete(ModelHasPermission).where(
                ModelHasPermission.model_id == user_id,
                ModelHasPermission.permission_id.in_(permission_ids)
            )
        )
        await self.db.commit()
