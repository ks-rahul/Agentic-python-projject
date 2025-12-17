"""Chat Builder seeder for default chat widget configurations."""
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_builder import ChatBuilder
from app.models.tenant import Tenant


# Default chat builder configurations
DEFAULT_CHAT_BUILDERS: List[Dict[str, Any]] = [
    {
        "name": "Default Chat Widget",
        "description": "Default chat widget configuration",
        "status": "active",
        "widget_title": "Chat with us",
        "widget_subtitle": "We typically reply within minutes",
        "primary_color": "#007bff",
        "secondary_color": "#6c757d",
        "position": "bottom-right",
        "auto_open": False,
        "show_typing_indicator": True,
        "enable_file_upload": False,
        "enable_voice_input": False,
        "config": {
            "theme": "light",
            "border_radius": "12px",
            "font_family": "Inter, sans-serif",
            "show_branding": True,
            "show_timestamp": True,
            "enable_emoji": True,
            "enable_markdown": True,
            "max_message_length": 2000,
            "placeholder_text": "Type your message...",
            "send_button_text": "Send",
        }
    },
    {
        "name": "Dark Theme Widget",
        "description": "Dark themed chat widget",
        "status": "active",
        "widget_title": "Need Help?",
        "widget_subtitle": "Our AI assistant is here to help",
        "primary_color": "#6366f1",
        "secondary_color": "#4f46e5",
        "position": "bottom-right",
        "auto_open": False,
        "show_typing_indicator": True,
        "enable_file_upload": True,
        "enable_voice_input": False,
        "config": {
            "theme": "dark",
            "border_radius": "16px",
            "font_family": "Inter, sans-serif",
            "show_branding": False,
            "show_timestamp": True,
            "enable_emoji": True,
            "enable_markdown": True,
            "max_message_length": 4000,
            "placeholder_text": "Ask me anything...",
            "send_button_text": "Send",
        }
    },
    {
        "name": "Minimal Widget",
        "description": "Minimal and clean chat widget",
        "status": "active",
        "widget_title": "Support",
        "widget_subtitle": None,
        "primary_color": "#10b981",
        "secondary_color": "#059669",
        "position": "bottom-left",
        "auto_open": False,
        "show_typing_indicator": True,
        "enable_file_upload": False,
        "enable_voice_input": False,
        "config": {
            "theme": "light",
            "border_radius": "8px",
            "font_family": "system-ui, sans-serif",
            "show_branding": False,
            "show_timestamp": False,
            "enable_emoji": False,
            "enable_markdown": False,
            "max_message_length": 1000,
            "placeholder_text": "Message...",
            "send_button_text": "→",
        }
    },
]


class ChatBuilderSeeder:
    """Seeder for default chat builder configurations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def seed(
        self, 
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "chat_builders_created": 0,
            "chat_builders_skipped": 0,
        }
        
        # Get tenant_id if not provided
        if not tenant_id:
            tenant_result = await self.db.execute(
                select(Tenant).limit(1)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                tenant_id = str(tenant.id)
            else:
                # No tenant exists, skip seeding
                return result
        
        for builder_data in DEFAULT_CHAT_BUILDERS:
            await self._seed_chat_builder(builder_data, tenant_id, user_id, result)
        
        await self.db.commit()
        return result
    
    async def _seed_chat_builder(
        self,
        builder_data: Dict[str, Any],
        tenant_id: str,
        user_id: Optional[str],
        result: Dict[str, int]
    ) -> None:
        """Seed a single chat builder."""
        # Check if exists by name and tenant
        existing = await self.db.execute(
            select(ChatBuilder).where(
                ChatBuilder.name == builder_data["name"],
                ChatBuilder.tenant_id == tenant_id
            )
        )
        
        if existing.scalar_one_or_none():
            result["chat_builders_skipped"] += 1
            return
        
        chat_builder = ChatBuilder(
            tenant_id=tenant_id,
            created_by=user_id,
            name=builder_data["name"],
            description=builder_data.get("description"),
            status=builder_data.get("status", "draft"),
            widget_title=builder_data.get("widget_title", "Chat with us"),
            widget_subtitle=builder_data.get("widget_subtitle"),
            primary_color=builder_data.get("primary_color", "#007bff"),
            secondary_color=builder_data.get("secondary_color", "#6c757d"),
            position=builder_data.get("position", "bottom-right"),
            auto_open=builder_data.get("auto_open", False),
            show_typing_indicator=builder_data.get("show_typing_indicator", True),
            enable_file_upload=builder_data.get("enable_file_upload", False),
            enable_voice_input=builder_data.get("enable_voice_input", False),
            config=builder_data.get("config", {}),
        )
        
        self.db.add(chat_builder)
        result["chat_builders_created"] += 1
