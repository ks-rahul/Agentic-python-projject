"""Tenant schemas."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class TenantBase(BaseModel):
    name: str
    company_name: Optional[str] = None
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    domain: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    domain: Optional[str] = None
    profile_image: Optional[str] = None


class TenantResponse(TenantBase):
    id: UUID
    profile_image: Optional[str] = None
    status: str
    max_users: int
    subscription_plan: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int
