"""User seeder for creating default users."""
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.user import User
from app.models.role import Role, ModelHasRole, Permission, ModelHasPermission
from app.models.tenant import Tenant, TenantUser
from app.core.security import get_password_hash


# Default users to seed
DEFAULT_USERS: List[Dict[str, Any]] = [
    {
        "name": "Super Admin",
        "email": "superadmin@iffort.com",
        "password": "Test@123",
        "role": "super_admin",
        "status": "active",
        "create_tenant": True,
        "tenant_name": "System Admin"
    },
    {
        "name": "Admin User",
        "email": "admin@iffort.com",
        "password": "Test@123",
        "role": "admin",
        "status": "active",
        "create_tenant": True,
        "tenant_name": "Admin Tenant"
    },
    {
        "name": "Tenant Owner",
        "email": "owner@iffort.com",
        "password": "Test@123",
        "role": "tenant_owner",
        "status": "active",
        "create_tenant": True,
        "tenant_name": "Demo Tenant"
    },
]


class UserSeeder:
    """Seeder for default users."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._role_cache: Dict[str, Role] = {}
    
    async def seed(self, users: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Run the seeder."""
        users_to_seed = users or DEFAULT_USERS
        
        result = {
            "users_created": 0,
            "users_skipped": 0,
            "tenants_created": 0,
            "roles_assigned": 0,
            "permissions_assigned": 0,
        }
        
        # Cache roles
        await self._cache_roles()
        
        for user_data in users_to_seed:
            await self._seed_user(user_data, result)
        
        await self.db.commit()
        return result
    
    async def _cache_roles(self) -> None:
        """Cache all roles for quick lookup."""
        roles_result = await self.db.execute(
            select(Role).where(Role.guard_name == "api")
        )
        for role in roles_result.scalars().all():
            self._role_cache[role.name] = role
    
    async def _seed_user(self, user_data: Dict[str, Any], result: Dict[str, int]) -> None:
        """Seed a single user."""
        # Check if user exists
        existing = await self.db.execute(
            select(User).where(User.email == user_data["email"])
        )
        user = existing.scalar_one_or_none()
        
        if user:
            result["users_skipped"] += 1
            # Still assign role if not assigned
            await self._assign_role_to_user(user, user_data.get("role"), result)
            return
        
        # Create user
        user = User(
            name=user_data["name"],
            email=user_data["email"],
            password=get_password_hash(user_data["password"]),
            status=user_data.get("status", "active"),
            email_verified_at=datetime.now(timezone.utc),
        )
        self.db.add(user)
        await self.db.flush()
        result["users_created"] += 1
        
        # Create tenant if needed
        if user_data.get("create_tenant"):
            tenant = Tenant(
                created_by=user.id,
                name=user_data.get("tenant_name", f"{user_data['name']}'s Tenant"),
                status="active",
            )
            self.db.add(tenant)
            await self.db.flush()
            
            # Link user to tenant
            tenant_user = TenantUser(
                tenant_id=tenant.id,
                user_id=user.id,
            )
            self.db.add(tenant_user)
            result["tenants_created"] += 1
        
        # Assign role
        await self._assign_role_to_user(user, user_data.get("role"), result)
    
    async def _assign_role_to_user(
        self, 
        user: User, 
        role_name: Optional[str],
        result: Dict[str, int]
    ) -> None:
        """Assign role and permissions to user."""
        if not role_name:
            return
        
        role = self._role_cache.get(role_name)
        if not role:
            return
        
        # Check if role already assigned
        existing_role = await self.db.execute(
            select(ModelHasRole).where(
                ModelHasRole.model_id == user.id,
                ModelHasRole.role_id == role.id
            )
        )
        if existing_role.scalar_one_or_none():
            return
        
        # Assign role
        model_has_role = ModelHasRole(
            role_id=role.id,
            model_id=user.id,
            model_type="App\\Models\\User"
        )
        self.db.add(model_has_role)
        result["roles_assigned"] += 1
        
        # Get role permissions and assign to user
        permissions_result = await self.db.execute(
            select(Permission)
            .join(Role.permissions)
            .where(Role.id == role.id)
        )
        
        for permission in permissions_result.scalars().all():
            # Check if permission already assigned
            existing_perm = await self.db.execute(
                select(ModelHasPermission).where(
                    ModelHasPermission.model_id == user.id,
                    ModelHasPermission.permission_id == permission.id
                )
            )
            if existing_perm.scalar_one_or_none():
                continue
            
            model_has_permission = ModelHasPermission(
                permission_id=permission.id,
                model_id=user.id,
                model_type="App\\Models\\User"
            )
            self.db.add(model_has_permission)
            result["permissions_assigned"] += 1


class SuperAdminSeeder(UserSeeder):
    """Convenience seeder for just the superadmin user."""
    
    async def seed(self) -> Dict[str, Any]:
        """Seed only the superadmin user."""
        return await super().seed([DEFAULT_USERS[0]])
