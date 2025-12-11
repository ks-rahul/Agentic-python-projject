"""API V1 Router - combines all route modules."""
from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    users,
    tenants,
    agents,
    knowledge_bases,
    documents,
    assistants,
    chat_builders,
    leads,
    roles,
    sessions,
    chat,
    webhooks,
    website_scrapes,
    whatsapp,
)

api_router = APIRouter()

# Auth routes (no prefix, under /auth)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User routes
api_router.include_router(users.router, prefix="/user", tags=["Users"])

# Tenant routes
api_router.include_router(tenants.router, prefix="/tenant", tags=["Tenants"])

# Agent routes
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])

# Knowledge Base routes
api_router.include_router(knowledge_bases.router, prefix="/knowledge-base", tags=["Knowledge Base"])

# Document routes
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Website Scrape routes
api_router.include_router(website_scrapes.router, prefix="/website-scrapes", tags=["Website Scrapes"])

# Assistant routes
api_router.include_router(assistants.router, prefix="/assistants", tags=["Assistants"])

# Assistant Configuration routes
api_router.include_router(
    assistants.config_router, 
    prefix="/assistant-configurations", 
    tags=["Assistant Configurations"]
)

# Agent Assistant routes
api_router.include_router(
    assistants.agent_assistant_router, 
    prefix="/agent-assistants", 
    tags=["Agent Assistants"]
)

# Intent Configuration routes
api_router.include_router(
    assistants.intent_router, 
    prefix="/assistant-intent-configurations", 
    tags=["Intent Configurations"]
)

# Chat Builder routes
api_router.include_router(chat_builders.router, prefix="/chat-builders", tags=["Chat Builders"])

# Lead routes
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])

# Public Lead routes
api_router.include_router(leads.public_router, prefix="/public", tags=["Public"])

# Role routes
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])

# Permission routes
api_router.include_router(roles.permission_router, prefix="/permissions", tags=["Permissions"])

# Session routes (for chat sessions - MongoDB)
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])

# Chat routes (AI chat endpoints)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Webhook routes
api_router.include_router(webhooks.router, prefix="/webhook", tags=["Webhooks"])

# WhatsApp routes
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp"])

# OAuth routes
api_router.include_router(assistants.oauth_router, prefix="/oauth", tags=["OAuth"])
