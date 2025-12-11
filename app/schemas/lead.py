"""Lead schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class LeadFormFieldConfig(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = False
    placeholder: Optional[str] = None


class LeadFormBase(BaseModel):
    name: str
    description: Optional[str] = None
    fields: Optional[List[LeadFormFieldConfig]] = None
    is_active: Optional[bool] = True
    show_after_messages: Optional[str] = "3"
    trigger_condition: Optional[str] = None
    title: Optional[str] = "Get in touch"
    submit_button_text: Optional[str] = "Submit"
    success_message: Optional[str] = "Thank you for your submission!"


class LeadFormCreate(LeadFormBase):
    tenant_id: UUID
    agent_id: UUID


class LeadFormUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[LeadFormFieldConfig]] = None
    is_active: Optional[bool] = None
    show_after_messages: Optional[str] = None
    trigger_condition: Optional[str] = None
    title: Optional[str] = None
    submit_button_text: Optional[str] = None
    success_message: Optional[str] = None


class LeadFormResponse(LeadFormBase):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadFormListResponse(BaseModel):
    lead_forms: List[LeadFormResponse]
    total: int


# Lead schemas
class LeadBase(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None


class LeadCreate(LeadBase):
    tenant_id: UUID
    agent_id: UUID
    lead_form_id: Optional[UUID] = None
    session_id: Optional[str] = None


class PublicLeadCreate(LeadBase):
    agent_id: UUID
    session_id: Optional[str] = None


class LeadResponse(LeadBase):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    lead_form_id: Optional[UUID] = None
    session_id: Optional[str] = None
    status: str
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    leads: List[LeadResponse]
    total: int
