"""Permission seeder with app module support."""
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission
from app.models.app_module import AppModule


# Permissions organized by module (matching Laravel PermissionSeeder)
MODULE_PERMISSIONS: Dict[str, List[Dict[str, str]]] = {
    "dashboard": [
        {"name": "view-dashboard", "display_name": "View Dashboard", "description": "Access the dashboard"},
    ],
    "tenant_management": [
        {"name": "list-tenant", "display_name": "List Tenant", "description": "List all tenants"},
        {"name": "view-tenant", "display_name": "View Tenant", "description": "View tenant details"},
        {"name": "update-tenant", "display_name": "Update Tenant", "description": "Update tenant information"},
        {"name": "delete-tenant", "display_name": "Delete Tenant", "description": "Delete a tenant"},
        {"name": "create-tenant", "display_name": "Create Tenant", "description": "Create a new tenant"},
    ],
    "knowledge_base": [
        {"name": "create-knowledge-base", "display_name": "Create Knowledge Base", "description": "Create a knowledge base"},
        {"name": "list-knowledge-base", "display_name": "List Knowledge Bases", "description": "List all knowledge bases"},
        {"name": "view-knowledge-base", "display_name": "View Knowledge Base", "description": "View knowledge base details"},
        {"name": "update-knowledge-base", "display_name": "Update Knowledge Base", "description": "Update knowledge base information"},
        {"name": "delete-knowledge-base", "display_name": "Delete Knowledge Base", "description": "Delete a knowledge base"},
        {"name": "retrain-knowledge-base", "display_name": "Retrain Knowledge Base", "description": "Retrain a knowledge base"},
    ],
    "document_management": [
        {"name": "create-document", "display_name": "Create Document", "description": "Create a document"},
        {"name": "list-document", "display_name": "List Documents", "description": "List all documents"},
        {"name": "view-document", "display_name": "View Document", "description": "View document details"},
        {"name": "update-document", "display_name": "Update Document", "description": "Update document information"},
        {"name": "delete-document", "display_name": "Delete Document", "description": "Delete a document"},
    ],
    "agent_management": [
        {"name": "create-agent", "display_name": "Create Agent", "description": "Create an agent"},
        {"name": "list-agent", "display_name": "List Agents", "description": "List all agents"},
        {"name": "view-agent", "display_name": "View Agent", "description": "View agent details"},
        {"name": "configure-agent", "display_name": "Configure Agent", "description": "Configure an agent"},
        {"name": "update-agent", "display_name": "Update Agent", "description": "Update agent information"},
        {"name": "delete-agent", "display_name": "Delete Agent", "description": "Delete an agent"},
        {"name": "attach-knowledge-base-to-agent", "display_name": "Attach Knowledge Base To Agent", "description": "Attach a knowledge base to an agent"},
        {"name": "detach-knowledge-base-from-agent", "display_name": "Detach Knowledge Base From Agent", "description": "Detach a knowledge base from an agent"},
        {"name": "publish-agent", "display_name": "Publish Agent", "description": "Publish an agent"},
    ],
    "assistant_management": [
        {"name": "create-assistant", "display_name": "Create Assistant", "description": "Create an assistant"},
        {"name": "list-assistant", "display_name": "List Assistants", "description": "List all assistants"},
        {"name": "view-assistant", "display_name": "View Assistant", "description": "View assistant details"},
        {"name": "update-assistant", "display_name": "Update Assistant", "description": "Update assistant information"},
        {"name": "delete-assistant", "display_name": "Delete Assistant", "description": "Delete an assistant"},
        {"name": "configure-assistant", "display_name": "Configure Assistant", "description": "Configure an assistant"},
        {"name": "manage-agent-assistants", "display_name": "Manage Agent Assistants", "description": "Attach/detach assistants to/from agents"},
        {"name": "manage-agent-assistant-auth", "display_name": "Manage Agent Assistant Auth", "description": "Manage assistant authentication for agents"},
    ],
    "lead_form": [
        {"name": "create-lead-form", "display_name": "Create Lead Form", "description": "Create a lead form"},
        {"name": "list-lead-forms", "display_name": "List Lead Forms", "description": "List all lead forms"},
        {"name": "view-lead-form", "display_name": "View Lead Form", "description": "View lead form details"},
        {"name": "update-lead-form", "display_name": "Update Lead Form", "description": "Update lead form information"},
        {"name": "delete-lead-form", "display_name": "Delete Lead Form", "description": "Delete a lead form"},
    ],
    "lead": [
        {"name": "create-lead", "display_name": "Create Lead", "description": "Permission to create new leads"},
        {"name": "view-lead", "display_name": "View Lead", "description": "Permission to view leads"},
        {"name": "list-leads", "display_name": "List Leads", "description": "Permission to view list of leads"},
        {"name": "update-lead", "display_name": "Update Lead", "description": "Permission to edit existing leads"},
        {"name": "delete-lead", "display_name": "Delete Lead", "description": "Permission to delete leads"},
    ],
    "role_management": [
        {"name": "list-role", "display_name": "List Roles", "description": "List all roles"},
        {"name": "view-role", "display_name": "View Role", "description": "View role details"},
        {"name": "create-role", "display_name": "Create Role", "description": "Create a new role"},
        {"name": "update-role", "display_name": "Update Role", "description": "Update role information"},
        {"name": "delete-role", "display_name": "Delete Role", "description": "Delete a role"},
        {"name": "assign-permissions-to-role", "display_name": "Assign Permissions To Role", "description": "Assign permissions to a role"},
        {"name": "assign-permissions-to-user", "display_name": "Assign Permissions To User", "description": "Assign permissions to a user"},
        {"name": "assign-role-to-user", "display_name": "Assign Role To User", "description": "Assign a role to a user"},
        {"name": "detach-role-from-user", "display_name": "Detach Role From User", "description": "Detach a role from a user"},
        {"name": "detach-permissions-from-role", "display_name": "Detach Permissions From Role", "description": "Detach permissions from a role"},
        {"name": "detach-permissions-from-user", "display_name": "Detach Permissions From User", "description": "Detach permissions from a user"},
        {"name": "list-permissions", "display_name": "List Permissions", "description": "List all permissions"},
        {"name": "view-permission", "display_name": "View Permission", "description": "View permission details"},
        {"name": "create-permission", "display_name": "Create Permission", "description": "Create a new permission"},
        {"name": "update-permission", "display_name": "Update Permission", "description": "Update permission information"},
        {"name": "delete-permission", "display_name": "Delete Permission", "description": "Delete a permission"},
        {"name": "view-role-for-form", "display_name": "View Roles For Form", "description": "Get roles for form"},
    ],
    "user_management": [
        {"name": "list-user", "display_name": "List Users", "description": "List all users"},
        {"name": "view-user", "display_name": "View User", "description": "View user details"},
        {"name": "create-user", "display_name": "Create User", "description": "Create a new user"},
        {"name": "update-user", "display_name": "Update User", "description": "Update user information"},
        {"name": "delete-user", "display_name": "Delete User", "description": "Delete a user"},
    ],
    "observability_management": [
        {"name": "view-observability", "display_name": "View Observability", "description": "Access observability features"},
        {"name": "view-observability-dashboard", "display_name": "View Observability Dashboard", "description": "View the observability dashboard"},
        {"name": "view-observability-usage", "display_name": "View API Usage", "description": "View API usage metrics"},
        {"name": "view-observability-performance", "display_name": "View Performance Metrics", "description": "View performance monitoring data"},
        {"name": "view-observability-endpoints", "display_name": "View Endpoint Metrics", "description": "View endpoint-specific metrics"},
        {"name": "view-observability-health", "display_name": "View System Health", "description": "View system health and status"},
        {"name": "view-observability-cache", "display_name": "View Cache Metrics", "description": "View cache performance and statistics"},
        {"name": "view-observability-personal", "display_name": "View Personal Metrics", "description": "View personal observability data"},
        {"name": "export-observability-data", "display_name": "Export Observability Data", "description": "Export observability metrics and data"},
    ],
}


class PermissionSeeder:
    """Seeder for permissions with app module support."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._module_cache: Dict[str, AppModule] = {}
    
    async def seed(self) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "permissions_created": 0,
            "permissions_skipped": 0,
            "permissions_updated": 0,
        }
        
        # Cache app modules
        await self._cache_modules()
        
        # Seed permissions for each module
        for module_name, permissions in MODULE_PERMISSIONS.items():
            module = self._module_cache.get(module_name)
            module_id = str(module.id) if module else None
            
            for perm_data in permissions:
                await self._seed_permission(perm_data, module_id, result)
        
        await self.db.commit()
        return result
    
    async def _cache_modules(self) -> None:
        """Cache all app modules."""
        modules_result = await self.db.execute(select(AppModule))
        for module in modules_result.scalars().all():
            self._module_cache[module.name] = module
    
    async def _seed_permission(
        self,
        perm_data: Dict[str, str],
        module_id: str,
        result: Dict[str, int]
    ) -> None:
        """Seed a single permission."""
        existing = await self.db.execute(
            select(Permission).where(Permission.name == perm_data["name"])
        )
        permission = existing.scalar_one_or_none()
        
        if permission:
            # Update existing permission
            permission.display_name = perm_data.get("display_name")
            permission.description = perm_data.get("description")
            if module_id:
                permission.app_module_id = module_id
            result["permissions_updated"] += 1
        else:
            # Create new permission
            permission = Permission(
                name=perm_data["name"],
                display_name=perm_data.get("display_name"),
                description=perm_data.get("description"),
                guard_name="api",
                app_module_id=module_id,
                is_active=True,
            )
            self.db.add(permission)
            result["permissions_created"] += 1
