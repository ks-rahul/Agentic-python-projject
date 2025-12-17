"""Lead seeder - creates lead module, permissions, and syncs with roles."""
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_module import AppModule
from app.models.role import Role, Permission, RoleHasPermission


# Lead permissions matching Laravel LeadSeeder
LEAD_PERMISSIONS: List[Dict[str, str]] = [
    {
        "name": "create-lead",
        "display_name": "Create Lead",
        "description": "Permission to create new leads",
    },
    {
        "name": "view-lead",
        "display_name": "View Lead",
        "description": "Permission to view leads",
    },
    {
        "name": "list-leads",
        "display_name": "List Leads",
        "description": "Permission to view list of leads",
    },
    {
        "name": "update-lead",
        "display_name": "Update Lead",
        "description": "Permission to edit existing leads",
    },
    {
        "name": "delete-lead",
        "display_name": "Delete Lead",
        "description": "Permission to delete leads",
    },
]

# Role permission mapping for leads
ROLE_LEAD_PERMISSIONS: Dict[str, List[str]] = {
    "super_admin": ["create-lead", "view-lead", "list-leads", "update-lead", "delete-lead"],
    "tenant_owner": ["create-lead", "view-lead", "list-leads", "update-lead", "delete-lead"],
    "executive": ["view-lead", "list-leads"],
    "tenant_executive": ["view-lead", "list-leads"],
    "admin": ["create-lead", "view-lead", "list-leads", "update-lead"],
    "user": ["view-lead", "list-leads"],
    "viewer": ["view-lead", "list-leads"],
}


class LeadSeeder:
    """Seeder for lead module, permissions, and role syncing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._permission_cache: Dict[str, Permission] = {}

    async def seed(self) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "module_created": False,
            "module_skipped": False,
            "permissions_created": 0,
            "permissions_skipped": 0,
            "role_permissions_attached": 0,
        }

        # 1. Create or get lead module
        lead_module = await self._seed_lead_module(result)

        # 2. Create lead permissions
        await self._seed_lead_permissions(lead_module, result)

        # 3. Sync permissions with roles
        await self._sync_role_permissions(result)

        await self.db.commit()
        return result

    async def _seed_lead_module(self, result: Dict[str, Any]) -> AppModule:
        """Create or get the lead app module."""
        existing = await self.db.execute(
            select(AppModule).where(AppModule.name == "lead")
        )
        module = existing.scalar_one_or_none()

        if module:
            result["module_skipped"] = True
        else:
            module = AppModule(
                name="lead",
                display_name="Leads",
                description="Manage leads",
                is_active=True,
            )
            self.db.add(module)
            await self.db.flush()
            result["module_created"] = True

        return module

    async def _seed_lead_permissions(
        self, module: AppModule, result: Dict[str, Any]
    ) -> None:
        """Create lead permissions."""
        for perm_data in LEAD_PERMISSIONS:
            existing = await self.db.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            permission = existing.scalar_one_or_none()

            if permission:
                self._permission_cache[perm_data["name"]] = permission
                result["permissions_skipped"] += 1
            else:
                permission = Permission(
                    name=perm_data["name"],
                    display_name=perm_data["display_name"],
                    description=perm_data["description"],
                    app_module_id=str(module.id),
                    guard_name="api",
                    is_active=True,
                )
                self.db.add(permission)
                await self.db.flush()
                self._permission_cache[perm_data["name"]] = permission
                result["permissions_created"] += 1

    async def _sync_role_permissions(self, result: Dict[str, Any]) -> None:
        """Sync lead permissions with roles."""
        for role_name, permission_names in ROLE_LEAD_PERMISSIONS.items():
            # Get role
            role_result = await self.db.execute(
                select(Role).where(Role.name == role_name)
            )
            role = role_result.scalar_one_or_none()

            if not role:
                continue

            # Attach permissions
            for perm_name in permission_names:
                if perm_name not in self._permission_cache:
                    continue

                permission = self._permission_cache[perm_name]

                # Check if already attached
                existing_link = await self.db.execute(
                    select(RoleHasPermission).where(
                        RoleHasPermission.role_id == role.id,
                        RoleHasPermission.permission_id == permission.id,
                    )
                )
                if not existing_link.scalar_one_or_none():
                    rhp = RoleHasPermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                    self.db.add(rhp)
                    result["role_permissions_attached"] += 1
