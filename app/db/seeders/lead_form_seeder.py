"""Lead Form seeder for default lead form configurations."""
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import LeadForm
from app.models.tenant import Tenant
from app.models.agent import Agent


# Default lead form field configurations
DEFAULT_LEAD_FORM_FIELDS = [
    {
        "name": "name",
        "label": "Full Name",
        "type": "text",
        "required": True,
        "placeholder": "Enter your full name",
        "order": 1
    },
    {
        "name": "email",
        "label": "Email Address",
        "type": "email",
        "required": True,
        "placeholder": "Enter your email",
        "order": 2
    },
    {
        "name": "phone",
        "label": "Phone Number",
        "type": "tel",
        "required": False,
        "placeholder": "Enter your phone number",
        "order": 3
    },
    {
        "name": "company",
        "label": "Company Name",
        "type": "text",
        "required": False,
        "placeholder": "Enter your company name",
        "order": 4
    },
    {
        "name": "message",
        "label": "Message",
        "type": "textarea",
        "required": False,
        "placeholder": "How can we help you?",
        "order": 5
    },
]


# Default lead form configurations
DEFAULT_LEAD_FORMS: List[Dict[str, Any]] = [
    {
        "name": "Contact Form",
        "description": "Standard contact form for lead capture",
        "fields": DEFAULT_LEAD_FORM_FIELDS,
        "is_active": True,
        "show_after_messages": "3",
        "trigger_condition": "user_engaged",
        "title": "Get in touch",
        "submit_button_text": "Submit",
        "success_message": "Thank you for your submission! We'll get back to you soon."
    },
    {
        "name": "Quick Contact",
        "description": "Minimal contact form with essential fields only",
        "fields": [
            {
                "name": "name",
                "label": "Name",
                "type": "text",
                "required": True,
                "placeholder": "Your name",
                "order": 1
            },
            {
                "name": "email",
                "label": "Email",
                "type": "email",
                "required": True,
                "placeholder": "Your email",
                "order": 2
            },
        ],
        "is_active": True,
        "show_after_messages": "5",
        "trigger_condition": "user_request",
        "title": "Leave your details",
        "submit_button_text": "Send",
        "success_message": "Thanks! We'll be in touch."
    },
    {
        "name": "Sales Inquiry",
        "description": "Lead form for sales inquiries",
        "fields": [
            {
                "name": "name",
                "label": "Full Name",
                "type": "text",
                "required": True,
                "placeholder": "Enter your full name",
                "order": 1
            },
            {
                "name": "email",
                "label": "Work Email",
                "type": "email",
                "required": True,
                "placeholder": "Enter your work email",
                "order": 2
            },
            {
                "name": "phone",
                "label": "Phone Number",
                "type": "tel",
                "required": True,
                "placeholder": "Enter your phone number",
                "order": 3
            },
            {
                "name": "company",
                "label": "Company",
                "type": "text",
                "required": True,
                "placeholder": "Company name",
                "order": 4
            },
            {
                "name": "company_size",
                "label": "Company Size",
                "type": "select",
                "required": False,
                "options": ["1-10", "11-50", "51-200", "201-500", "500+"],
                "order": 5
            },
            {
                "name": "budget",
                "label": "Budget Range",
                "type": "select",
                "required": False,
                "options": ["< $1,000", "$1,000 - $5,000", "$5,000 - $10,000", "$10,000+"],
                "order": 6
            },
            {
                "name": "message",
                "label": "How can we help?",
                "type": "textarea",
                "required": False,
                "placeholder": "Tell us about your needs",
                "order": 7
            },
        ],
        "is_active": True,
        "show_after_messages": "2",
        "trigger_condition": "sales_intent",
        "title": "Request a Demo",
        "submit_button_text": "Request Demo",
        "success_message": "Thank you for your interest! Our sales team will contact you within 24 hours."
    },
]


class LeadFormSeeder:
    """Seeder for default lead form configurations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def seed(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the seeder."""
        result = {
            "lead_forms_created": 0,
            "lead_forms_skipped": 0,
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
                return result
        
        # Get agent_id if not provided
        if not agent_id:
            agent_result = await self.db.execute(
                select(Agent).where(Agent.tenant_id == tenant_id).limit(1)
            )
            agent = agent_result.scalar_one_or_none()
            if agent:
                agent_id = str(agent.id)
            else:
                # Create a default agent for lead forms
                return result
        
        for form_data in DEFAULT_LEAD_FORMS:
            await self._seed_lead_form(form_data, tenant_id, agent_id, result)
        
        await self.db.commit()
        return result
    
    async def _seed_lead_form(
        self,
        form_data: Dict[str, Any],
        tenant_id: str,
        agent_id: str,
        result: Dict[str, int]
    ) -> None:
        """Seed a single lead form."""
        # Check if exists by name and tenant
        existing = await self.db.execute(
            select(LeadForm).where(
                LeadForm.name == form_data["name"],
                LeadForm.tenant_id == tenant_id
            )
        )
        
        if existing.scalar_one_or_none():
            result["lead_forms_skipped"] += 1
            return
        
        lead_form = LeadForm(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=form_data["name"],
            description=form_data.get("description"),
            fields=form_data.get("fields", DEFAULT_LEAD_FORM_FIELDS),
            is_active=form_data.get("is_active", True),
            show_after_messages=form_data.get("show_after_messages", "3"),
            trigger_condition=form_data.get("trigger_condition"),
            title=form_data.get("title", "Get in touch"),
            submit_button_text=form_data.get("submit_button_text", "Submit"),
            success_message=form_data.get("success_message", "Thank you for your submission!"),
        )
        
        self.db.add(lead_form)
        result["lead_forms_created"] += 1
