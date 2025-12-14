"""Assistant management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.schemas.assistant import (
    AssistantCreate, AssistantUpdate, AssistantResponse, AssistantListResponse,
    SaveAssistantConfigurationRequest, GenerateCodeRequest, UpdateGeneratedCodeRequest,
    InvokePlaygroundRequest, DeployAssistantRequest,
    AttachAssistantRequest, DetachAssistantRequest, UpdateAgentAssistantAuthRequest,
    IntentConfigurationCreate, IntentConfigurationUpdate, IntentConfigurationResponse,
    IntentConfigurationListResponse
)
from app.services.assistant_service import AssistantService
from app.core.security import get_current_user

router = APIRouter()
config_router = APIRouter()
agent_assistant_router = APIRouter()
intent_router = APIRouter()
oauth_router = APIRouter()


# Public endpoint for assistant configurations (no auth required)
@router.get("/configurations")
async def get_assistant_configurations(
    db: AsyncSession = Depends(get_db)
):
    """Get all assistant configurations (public endpoint for chat widget)."""
    assistant_service = AssistantService(db)
    configurations = await assistant_service.get_all_configurations()
    return {"configurations": configurations}


# Assistant routes
@router.get("/list", response_model=AssistantListResponse)
async def list_assistants(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all assistants."""
    assistant_service = AssistantService(db)
    assistants = await assistant_service.list_assistants(current_user.get("tenant_id"))
    
    return AssistantListResponse(
        assistants=assistants,
        total=len(assistants)
    )


@router.get("/get/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get assistant by ID."""
    assistant_service = AssistantService(db)
    assistant = await assistant_service.get_by_id(str(assistant_id))
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    return assistant


@router.post("/create", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    request: AssistantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new assistant."""
    assistant_service = AssistantService(db)
    
    assistant = await assistant_service.create(
        tenant_id=str(request.tenant_id),
        created_by=current_user["user_id"],
        name=request.name,
        description=request.description,
        icon=request.icon
    )
    
    return assistant


@router.post("/update/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    request: AssistantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update assistant."""
    assistant_service = AssistantService(db)
    
    assistant = await assistant_service.get_by_id(str(assistant_id))
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    updated = await assistant_service.update(
        str(assistant_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated


@router.delete("/delete/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete assistant."""
    assistant_service = AssistantService(db)
    
    assistant = await assistant_service.get_by_id(str(assistant_id))
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    await assistant_service.delete(str(assistant_id))
    return None


@router.post("/generate-code")
async def generate_assistant_code(
    request: GenerateCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate code for assistant."""
    assistant_service = AssistantService(db)
    result = await assistant_service.generate_code(
        str(request.assistant_id),
        request.prompt
    )
    return result


@router.post("/update-generated-code")
async def update_generated_code(
    request: UpdateGeneratedCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update generated code for assistant."""
    assistant_service = AssistantService(db)
    await assistant_service.update(
        str(request.assistant_id),
        generated_code=request.code
    )
    return {"message": "Code updated successfully"}


@router.post("/invoke-playground-method")
async def invoke_playground_method(
    request: InvokePlaygroundRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Invoke assistant method in playground."""
    assistant_service = AssistantService(db)
    result = await assistant_service.invoke_method(
        str(request.assistant_id),
        request.method_name,
        request.parameters
    )
    return result


@router.post("/deploy")
async def deploy_assistant(
    request: DeployAssistantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deploy assistant."""
    assistant_service = AssistantService(db)
    result = await assistant_service.deploy(
        str(request.assistant_id),
        request.deployment_config
    )
    return result


# Configuration routes
@config_router.post("/save")
async def save_assistant_configuration(
    request: SaveAssistantConfigurationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Save assistant configurations."""
    assistant_service = AssistantService(db)
    await assistant_service.save_configurations(
        str(request.assistant_id),
        request.configurations
    )
    return {"message": "Configurations saved successfully"}


# Agent Assistant routes
@agent_assistant_router.post("/attach")
async def attach_assistant_to_agent(
    request: AttachAssistantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Attach assistant to agent."""
    assistant_service = AssistantService(db)
    await assistant_service.attach_to_agent(
        str(request.agent_id),
        str(request.assistant_id),
        request.required_tenant_auth,
        request.auth_configurations
    )
    return {"message": "Assistant attached successfully"}


@agent_assistant_router.post("/detach")
async def detach_assistant_from_agent(
    request: DetachAssistantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detach assistant from agent."""
    assistant_service = AssistantService(db)
    await assistant_service.detach_from_agent(
        str(request.agent_id),
        str(request.assistant_id)
    )
    return {"message": "Assistant detached successfully"}


@agent_assistant_router.post("/update-auth")
async def update_agent_assistant_auth(
    request: UpdateAgentAssistantAuthRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update agent assistant auth credentials."""
    assistant_service = AssistantService(db)
    await assistant_service.update_agent_assistant_auth(
        str(request.agent_id),
        str(request.assistant_id),
        request.auth_credentials
    )
    return {"message": "Auth credentials updated successfully"}


@agent_assistant_router.get("/agent/{agent_id}")
async def get_agent_assistants(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get assistants for an agent."""
    assistant_service = AssistantService(db)
    assistants = await assistant_service.get_agent_assistants(str(agent_id))
    return {"assistants": assistants}


# Intent Configuration routes
@intent_router.get("/list", response_model=IntentConfigurationListResponse)
async def list_intent_configurations(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all intent configurations."""
    assistant_service = AssistantService(db)
    configs = await assistant_service.list_intent_configurations(
        current_user.get("tenant_id")
    )
    
    return IntentConfigurationListResponse(
        configurations=configs,
        total=len(configs)
    )


@intent_router.get("/get/{config_id}", response_model=IntentConfigurationResponse)
async def get_intent_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get intent configuration by ID."""
    assistant_service = AssistantService(db)
    config = await assistant_service.get_intent_configuration(str(config_id))
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent configuration not found"
        )
    
    return config


@intent_router.post("/create", response_model=IntentConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_intent_configuration(
    request: IntentConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create intent configuration."""
    assistant_service = AssistantService(db)
    config = await assistant_service.create_intent_configuration(request)
    return config


@intent_router.put("/update/{config_id}", response_model=IntentConfigurationResponse)
async def update_intent_configuration(
    config_id: UUID,
    request: IntentConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update intent configuration."""
    assistant_service = AssistantService(db)
    config = await assistant_service.update_intent_configuration(
        str(config_id),
        request
    )
    return config


@intent_router.delete("/delete/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_configuration(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete intent configuration."""
    assistant_service = AssistantService(db)
    await assistant_service.delete_intent_configuration(str(config_id))
    return None


@intent_router.get("/by-agent/{agent_id}")
async def get_intent_configurations_by_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get intent configurations by agent."""
    assistant_service = AssistantService(db)
    configs = await assistant_service.get_intent_configurations_by_agent(str(agent_id))
    return {"configurations": configs}


@intent_router.get("/by-tenant/{tenant_id}")
async def get_intent_configurations_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get intent configurations by tenant."""
    assistant_service = AssistantService(db)
    configs = await assistant_service.list_intent_configurations(str(tenant_id))
    return {"configurations": configs}


# OAuth routes
@oauth_router.post("/initialize")
async def initialize_oauth(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Initialize OAuth flow for assistant."""
    assistant_service = AssistantService(db)
    result = await assistant_service.initialize_oauth(str(assistant_id))
    return result


@oauth_router.post("/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback."""
    assistant_service = AssistantService(db)
    result = await assistant_service.handle_oauth_callback(code, state)
    return result


@oauth_router.post("/refresh-token")
async def refresh_oauth_token(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Refresh OAuth token."""
    assistant_service = AssistantService(db)
    result = await assistant_service.refresh_oauth_token(str(assistant_id))
    return result


@oauth_router.delete("/revoke/{assistant_id}")
async def revoke_oauth_token(
    assistant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Revoke OAuth token."""
    assistant_service = AssistantService(db)
    await assistant_service.revoke_oauth_token(str(assistant_id))
    return {"message": "Token revoked successfully"}
