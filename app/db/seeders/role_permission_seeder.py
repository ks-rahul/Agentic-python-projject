"""Role and Permission seeder."""
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role, Permission, RoleHasPermission


# Define all permissions grouped by module (matching Laravel PermissionSeeder)
PERMISSIONS: Dict[str, List[Dict[str, str]]] = {
    "dashboard": [
        {"name": "view-dashboard", "description": "Access the dashboard"},
    ],
    "tenant_management": [
        {"name": "list-tenant", "description": "List all tenants"},
        {"name": "view-tenant", "description": "View tenant details"},
        {"name": "create-tenant", "description": "Create a new tenant"},
        {"name": "update-tenant", "description": "Update tenant information"},
        {"name": "delete-tenant", "description": "Delete a tenant"},
    ],
    "knowledge_base": [
        {"name": "create-knowledge-base", "description": "Create a knowledge base"},
        {"name": "list-knowledge-base", "description": "List all knowledge bases"},
        {"name": "view-knowledge-base", "description": "View knowledge base details"},
        {"name": "update-knowledge-base", "description": "Update knowledge base information"},
        {"name": "delete-knowledge-base", "description": "Delete a knowledge base"},
        {"name": "retrain-knowledge-base", "description": "Retrain a knowledge base"},
    ],
    "document_management": [
        {"name": "create-document", "description": "Create a document"},
        {"name": "list-document", "description": "List all documents"},
        {"name": "view-document", "description": "View document details"},
        {"name": "update-document", "description": "Update document information"},
        {"name": "delete-document", "description": "Delete a document"},
    ],
    "agent_management": [
        {"name": "create-agent", "description": "Create an agent"},
        {"name": "list-agent", "description": "List all agents"},
        {"name": "view-agent", "description": "View agent details"},
        {"name": "configure-agent", "description": "Configure an agent"},
        {"name": "update-agent", "description": "Update agent information"},
        {"name": "delete-agent", "description": "Delete an agent"},
        {"name": "attach-knowledge-base-to-agent", "description": "Attach a knowledge base to an agent"},
        {"name": "detach-knowledge-base-from-agent", "description": "Detach a knowledge base from an agent"},
        {"name": "publish-agent", "description": "Publish an agent"},
    ],
    "assistant_management": [
        {"name": "create-assistant", "description": "Create an assistant"},
        {"name": "list-assistant", "description": "List all assistants"},
        {"name": "view-assistant", "description": "View assistant details"},
        {"name": "update-assistant", "description": "Update assistant information"},
        {"name": "delete-assistant", "description": "Delete an assistant"},
        {"name": "configure-assistant", "description": "Configure an assistant"},
        {"name": "manage-agent-assistants", "description": "Attach/detach assistants to/from agents"},
        {"name": "manage-agent-assistant-auth", "description": "Manage assistant authentication for agents"},
    ],
    "lead_form": [
        {"name": "create-lead-form", "description": "Create a lead form"},
        {"name": "list-lead-forms", "description": "List all lead forms"},
        {"name": "view-lead-form", "description": "View lead form details"},
        {"name": "update-lead-form", "description": "Update lead form information"},
        {"name": "delete-lead-form", "description": "Delete a lead form"},
    ],
    "lead": [
        {"name": "create-lead", "description": "Permission to create new leads"},
        {"name": "view-lead", "description": "Permission to view leads"},
        {"name": "list-leads", "description": "Permission to view list of leads"},
        {"name": "update-lead", "description": "Permission to edit existing leads"},
        {"name": "delete-lead", "description": "Permission to delete leads"},
    ],
    "role_management": [
        {"name": "list-role", "description": "List all roles"},
        {"name": "view-role", "description": "View role details"},
        {"name": "create-role", "description": "Create a new role"},
        {"name": "update-role", "description": "Update role information"},
        {"name": "delete-role", "description": "Delete a role"},
        {"name": "assign-permissions-to-role", "description": "Assign permissions to a role"},
        {"name": "assign-permissions-to-user", "description": "Assign permissions to a user"},
        {"name": "assign-role-to-user", "description": "Assign a role to a user"},
        {"name": "detach-role-from-user", "description": "Detach a role from a user"},
        {"name": "detach-permissions-from-role", "description": "Detach permissions from a role"},
        {"name": "detach-permissions-from-user", "description": "Detach permissions from a user"},
        {"name": "list-permissions", "description": "List all permissions"},
        {"name": "view-permission", "description": "View permission details"},
        {"name": "create-permission", "description": "Create a new permission"},
        {"name": "update-permission", "description": "Update permission information"},
        {"name": "delete-permission", "description": "Delete a permission"},
        {"name": "view-role-for-form", "description": "Get roles for form"},
    ],
    "user_management": [
        {"name": "list-user", "description": "List all users"},
        {"name": "view-user", "description": "View user details"},
        {"name": "create-user", "description": "Create a new user"},
        {"name": "update-user", "description": "Update user information"},
        {"name": "delete-user", "description": "Delete a user"},
    ],
    "chat_builder": [
        {"name": "list-chat-builder", "description": "List all chat builders"},
        {"name": "view-chat-builder", "description": "View chat builder details"},
        {"name": "create-chat-builder", "description": "Create a chat builder"},
        {"name": "update-chat-builder", "description": "Update chat builder"},
        {"name": "delete-chat-builder", "description": "Delete a chat builder"},
    ],
    "website_scrape": [
        {"name": "list-website-scrape", "description": "List all website scrapes"},
        {"name": "view-website-scrape", "description": "View website scrape details"},
        {"name": "create-website-scrape", "description": "Create a website scrape"},
        {"name": "update-website-scrape", "description": "Update website scrape"},
        {"name": "delete-website-scrape", "description": "Delete a website scrape"},
    ],
    "whatsapp_integration": [
        {"name": "view-whatsapp", "description": "View WhatsApp integration"},
        {"name": "connect-whatsapp", "description": "Connect WhatsApp account"},
        {"name": "disconnect-whatsapp", "description": "Disconnect WhatsApp account"},
    ],
    "observability_management": [
        {"name": "view-observability", "description": "Access observability features"},
        {"name": "view-observability-dashboard", "description": "View the observability dashboard"},
        {"name": "view-observability-usage", "description": "View API usage metrics"},
        {"name": "view-observability-performance", "description": "View performance monitoring data"},
        {"name": "view-observability-endpoints", "description": "View endpoint-specific metrics"},
        {"name": "view-observability-health", "description": "View system health and status"},
        {"name": "view-observability-cache", "description": "View cache performance and statistics"},
        {"name": "view-observability-personal", "description": "View personal observability data"},
        {"name": "export-observability-data", "description": "Export observability metrics and data"},
    ],
}

# Define roles with their permissions (matching Laravel RolesAndPermissionsSeeder)
ROLES: List[Dict[str, Any]] = [
    {
        "name": "super_admin",
        "display_name": "Super Admin",
        "description": "Super Administrator with full access to all features",
        "type": "internal",
        "is_system_generated": True,
        "permissions": "*",  # All permissions
    },
    {
        "name": "executive",
        "display_name": "Executive",
        "description": "Executive with read access and user management",
        "type": "internal",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-tenant", "view-tenant",
            "list-knowledge-base", "view-knowledge-base",
            "list-document", "view-document",
            "list-agent", "view-agent",
            "list-role", "view-role",
            "list-permissions", "view-permission",
            "view-user", "list-user", "create-user", "update-user", "delete-user",
            "view-lead-form", "list-lead-forms",
            "view-lead", "list-leads",  # Lead permissions
            "manage-agent-assistants", "manage-agent-assistant-auth",
        ],
    },
    {
        "name": "tenant_owner",
        "display_name": "Tenant Owner",
        "description": "Tenant owner with full access to tenant resources",
        "type": "external",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-tenant", "view-tenant", "update-tenant",
            "create-knowledge-base", "list-knowledge-base", "view-knowledge-base",
            "update-knowledge-base", "delete-knowledge-base", "retrain-knowledge-base",
            "create-document", "list-document", "view-document",
            "update-document", "delete-document",
            "create-agent", "view-agent", "list-agent", "configure-agent",
            "update-agent", "delete-agent",
            "attach-knowledge-base-to-agent", "detach-knowledge-base-from-agent",
            "publish-agent",
            "list-assistant", "manage-agent-assistant-auth",
            "view-user", "list-user", "create-user", "update-user", "delete-user",
            "create-lead-form", "list-lead-forms", "view-lead-form",
            "update-lead-form", "delete-lead-form",
            # Lead permissions - full access
            "create-lead", "view-lead", "list-leads", "update-lead", "delete-lead",
            "view-role-for-form",
            "manage-agent-assistants", "manage-agent-assistant-auth",
            "list-chat-builder", "view-chat-builder", "create-chat-builder",
            "update-chat-builder", "delete-chat-builder",
            "list-website-scrape", "view-website-scrape", "create-website-scrape",
            "update-website-scrape", "delete-website-scrape",
            "view-whatsapp", "connect-whatsapp", "disconnect-whatsapp",
        ],
    },
    {
        "name": "tenant_executive",
        "display_name": "Tenant Executive",
        "description": "Tenant executive with read access",
        "type": "external",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-knowledge-base", "view-knowledge-base",
            "list-document", "view-document",
            "list-agent", "view-agent",
            "list-permissions", "view-permission",
            "view-user", "list-user", "create-user", "update-user", "delete-user",
            "view-lead-form",
            "view-lead", "list-leads",  # Lead permissions - read only
            "list-assistant",
            "manage-agent-assistant-auth",
            "manage-agent-assistants",
        ],
    },
    {
        "name": "admin",
        "display_name": "Admin",
        "description": "Administrator with management access",
        "type": "internal",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-tenant", "view-tenant", "update-tenant",
            "list-knowledge-base", "view-knowledge-base", "create-knowledge-base",
            "update-knowledge-base", "delete-knowledge-base",
            "list-document", "view-document", "create-document",
            "update-document", "delete-document",
            "list-agent", "view-agent", "create-agent", "update-agent",
            "configure-agent", "publish-agent",
            "attach-knowledge-base-to-agent", "detach-knowledge-base-from-agent",
            "list-assistant", "view-assistant", "create-assistant",
            "update-assistant", "configure-assistant",
            "manage-agent-assistants", "manage-agent-assistant-auth",
            "list-user", "view-user", "create-user", "update-user",
            "list-role", "view-role",
            "list-permissions", "view-permission",
            "list-lead-forms", "view-lead-form", "create-lead-form",
            "update-lead-form",
            "list-chat-builder", "view-chat-builder", "create-chat-builder",
            "update-chat-builder",
            "list-website-scrape", "view-website-scrape", "create-website-scrape",
            "view-whatsapp",
        ],
    },
    {
        "name": "user",
        "display_name": "User",
        "description": "Standard user with basic access",
        "type": "external",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-agent", "view-agent",
            "list-knowledge-base", "view-knowledge-base",
            "list-document", "view-document", "create-document",
            "list-assistant", "view-assistant",
            "list-chat-builder", "view-chat-builder",
            "view-lead-form",
        ],
    },
    {
        "name": "viewer",
        "display_name": "Viewer",
        "description": "Read-only access to resources",
        "type": "external",
        "is_system_generated": True,
        "permissions": [
            "view-dashboard",
            "list-agent", "view-agent",
            "list-knowledge-base", "view-knowledge-base",
            "list-document", "view-document",
            "list-assistant", "view-assistant",
            "list-chat-builder", "view-chat-builder",
            "view-lead-form",
        ],
    },
]


class RolePermissionSeeder:
    """Seeder for roles and permissions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._permission_cache: Dict[str, Permission] = {}
    
    async def seed(self) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "permissions_created": 0,
            "permissions_skipped": 0,
            "roles_created": 0,
            "roles_skipped": 0,
            "role_permissions_attached": 0,
        }
        
        # Seed permissions
        await self._seed_permissions(result)
        
        # Seed roles
        await self._seed_roles(result)
        
        await self.db.commit()
        return result
    
    async def _seed_permissions(self, result: Dict[str, int]) -> None:
        """Seed all permissions."""
        for module, perms in PERMISSIONS.items():
            for perm_data in perms:
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
                        description=perm_data["description"],
                        module=module,
                        guard_name="api",
                        is_active=True,
                    )
                    self.db.add(permission)
                    await self.db.flush()
                    self._permission_cache[perm_data["name"]] = permission
                    result["permissions_created"] += 1
    
    async def _seed_roles(self, result: Dict[str, int]) -> None:
        """Seed all roles with their permissions."""
        for role_data in ROLES:
            existing = await self.db.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            role = existing.scalar_one_or_none()
            
            if role:
                result["roles_skipped"] += 1
            else:
                role = Role(
                    name=role_data["name"],
                    display_name=role_data.get("display_name", role_data["name"].replace("_", " ").title()),
                    description=role_data["description"],
                    type=role_data.get("type", "internal"),
                    is_system_generated=role_data.get("is_system_generated", False),
                    guard_name="api",
                    is_active=True,
                )
                self.db.add(role)
                await self.db.flush()
                result["roles_created"] += 1
            
            # Attach permissions to role
            permission_names = self._resolve_permissions(role_data["permissions"])
            for perm_name in permission_names:
                if perm_name in self._permission_cache:
                    permission = self._permission_cache[perm_name]
                    
                    # Check if already attached
                    existing_link = await self.db.execute(
                        select(RoleHasPermission).where(
                            RoleHasPermission.role_id == role.id,
                            RoleHasPermission.permission_id == permission.id
                        )
                    )
                    if not existing_link.scalar_one_or_none():
                        rhp = RoleHasPermission(
                            role_id=role.id,
                            permission_id=permission.id
                        )
                        self.db.add(rhp)
                        result["role_permissions_attached"] += 1
    
    def _resolve_permissions(self, permissions: Any) -> List[str]:
        """Resolve permission patterns to actual permission names."""
        if permissions == "*":
            return list(self._permission_cache.keys())
        
        resolved = []
        for perm in permissions:
            if perm.endswith(".*"):
                # Wildcard for module
                module = perm[:-2]
                for name in self._permission_cache.keys():
                    if name.startswith(f"{module}."):
                        resolved.append(name)
            else:
                resolved.append(perm)
        
        return resolved
