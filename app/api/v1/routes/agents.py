"""Agent management routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse,
    AgentConfigureRequest, KnowledgeBaseAttachRequest, AgentConfigurationResponse
)
from app.services.agent_service import AgentService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all agents for current tenant."""
    agent_service = AgentService(db)
    agents = await agent_service.list_agents(current_user.get("tenant_id"))
    
    return AgentListResponse(
        agents=agents,
        total=len(agents)
    )


@router.get("/get/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get agent by ID."""
    agent_service = AgentService(db)
    agent = await agent_service.get_by_id(str(agent_id))
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent


@router.post("/create", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new agent."""
    agent_service = AgentService(db)
    
    tenant_id = request.tenant_id or current_user.get("tenant_id")
    agent = await agent_service.create(
        name=request.name,
        display_name=request.display_name,
        type=request.type,
        description=request.description,
        tenant_id=tenant_id,
        settings=request.settings
    )
    
    return agent


@router.put("/update/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update agent."""
    agent_service = AgentService(db)
    
    agent = await agent_service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    updated_agent = await agent_service.update(
        str(agent_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_agent


@router.delete("/delete/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete agent (soft delete)."""
    agent_service = AgentService(db)
    
    agent = await agent_service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    await agent_service.delete(str(agent_id))
    return None


@router.post("/configure")
async def configure_agent(
    request: AgentConfigureRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure agent settings."""
    agent_service = AgentService(db)
    
    agent = await agent_service.get_by_id(str(request.agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    await agent_service.configure_settings(
        str(request.agent_id),
        request.settings.model_dump()
    )
    
    return {"message": "Agent configured successfully"}


@router.post("/knowledge-base/attach")
async def attach_knowledge_base(
    request: KnowledgeBaseAttachRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Attach knowledge base to agent."""
    agent_service = AgentService(db)
    
    await agent_service.attach_knowledge_base(
        str(request.agent_id),
        str(request.knowledge_base_id)
    )
    
    return {"message": "Knowledge base attached successfully"}


@router.post("/knowledge-base/detach")
async def detach_knowledge_base(
    request: KnowledgeBaseAttachRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detach knowledge base from agent."""
    agent_service = AgentService(db)
    
    await agent_service.detach_knowledge_base(
        str(request.agent_id),
        str(request.knowledge_base_id)
    )
    
    return {"message": "Knowledge base detached successfully"}


@router.get("/publish-agent/{agent_id}")
async def publish_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Publish agent."""
    agent_service = AgentService(db)
    
    agent = await agent_service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    await agent_service.update(str(agent_id), status="published")
    
    return {"message": "Agent published successfully"}


@router.get("/unpublish-agent/{agent_id}")
async def unpublish_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Unpublish agent."""
    agent_service = AgentService(db)
    
    agent = await agent_service.get_by_id(str(agent_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    await agent_service.update(str(agent_id), status="draft")
    
    return {"message": "Agent unpublished successfully"}


# Public endpoint (no auth required)
@router.get("/get-agent-configuration/{agent_id}", response_model=AgentConfigurationResponse)
async def get_agent_configuration(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get full agent configuration (public endpoint for chat widget)."""
    agent_service = AgentService(db)
    config = await agent_service.get_full_configuration(str(agent_id))
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return config
