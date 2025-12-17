"""App Module seeder."""
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_module import AppModule


# Define all app modules
APP_MODULES: List[Dict[str, str]] = [
    {
        "name": "dashboard",
        "display_name": "Dashboard",
        "description": "Access to the dashboard"
    },
    {
        "name": "tenant_management",
        "display_name": "Tenant Management",
        "description": "Manage tenants"
    },
    {
        "name": "knowledge_base",
        "display_name": "Knowledge Base",
        "description": "Manage knowledge bases"
    },
    {
        "name": "document_management",
        "display_name": "Document Management",
        "description": "Manage documents"
    },
    {
        "name": "agent_management",
        "display_name": "Agent Management",
        "description": "Manage agents"
    },
    {
        "name": "assistant_management",
        "display_name": "Assistant Management",
        "description": "Manage assistants"
    },
    {
        "name": "lead_form",
        "display_name": "Lead Form",
        "description": "Manage lead forms and leads"
    },
    {
        "name": "lead",
        "display_name": "Leads",
        "description": "Manage leads"
    },
    {
        "name": "role_management",
        "display_name": "Role Management",
        "description": "Manage roles and permissions"
    },
    {
        "name": "user_management",
        "display_name": "User Management",
        "description": "Manage users"
    },
    {
        "name": "chat_builder",
        "display_name": "Chat Builder",
        "description": "Manage chat widget builders"
    },
    {
        "name": "website_scrape",
        "display_name": "Website Scrape",
        "description": "Manage website scraping"
    },
    {
        "name": "whatsapp_integration",
        "display_name": "WhatsApp Integration",
        "description": "Manage WhatsApp business integration"
    },
    {
        "name": "settings",
        "display_name": "Settings",
        "description": "Application settings management"
    },
    {
        "name": "observability_management",
        "display_name": "Observability Management",
        "description": "System observability and metrics"
    },
]


class AppModuleSeeder:
    """Seeder for app modules."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def seed(self) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "modules_created": 0,
            "modules_skipped": 0,
        }
        
        for module_data in APP_MODULES:
            existing = await self.db.execute(
                select(AppModule).where(AppModule.name == module_data["name"])
            )
            module = existing.scalar_one_or_none()
            
            if module:
                result["modules_skipped"] += 1
            else:
                module = AppModule(
                    name=module_data["name"],
                    display_name=module_data["display_name"],
                    description=module_data["description"],
                    is_active=True,
                )
                self.db.add(module)
                result["modules_created"] += 1
        
        await self.db.commit()
        return result
