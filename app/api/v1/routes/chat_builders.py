"""Chat Builder management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.schemas.chat_builder import (
    ChatBuilderCreate, ChatBuilderUpdate, ChatBuilderResponse,
    ChatBuilderListResponse, ConfigureChatBuilderRequest
)
from app.services.chat_builder_service import ChatBuilderService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/list", response_model=ChatBuilderListResponse)
async def list_chat_builders(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all chat builders."""
    cb_service = ChatBuilderService(db)
    chat_builders = await cb_service.list_by_tenant(current_user.get("tenant_id"))
    
    return ChatBuilderListResponse(
        chat_builders=chat_builders,
        total=len(chat_builders)
    )


@router.get("/get/{cb_id}", response_model=ChatBuilderResponse)
async def get_chat_builder(
    cb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get chat builder by ID."""
    cb_service = ChatBuilderService(db)
    cb = await cb_service.get_by_id(str(cb_id))
    
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat builder not found"
        )
    
    return cb


@router.post("/create", response_model=ChatBuilderResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_builder(
    request: ChatBuilderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat builder."""
    cb_service = ChatBuilderService(db)
    
    cb = await cb_service.create(
        tenant_id=str(request.tenant_id),
        created_by=current_user["user_id"],
        **request.model_dump(exclude={"tenant_id"})
    )
    
    return cb


@router.put("/update/{cb_id}", response_model=ChatBuilderResponse)
async def update_chat_builder(
    cb_id: UUID,
    request: ChatBuilderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update chat builder."""
    cb_service = ChatBuilderService(db)
    
    cb = await cb_service.get_by_id(str(cb_id))
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat builder not found"
        )
    
    updated_cb = await cb_service.update(
        str(cb_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_cb


@router.delete("/delete/{cb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_builder(
    cb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete chat builder (soft delete)."""
    cb_service = ChatBuilderService(db)
    
    cb = await cb_service.get_by_id(str(cb_id))
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat builder not found"
        )
    
    await cb_service.delete(str(cb_id))
    return None


@router.post("/configure")
async def configure_chat_builder(
    request: ConfigureChatBuilderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Configure chat builder with agents."""
    cb_service = ChatBuilderService(db)
    
    cb = await cb_service.get_by_id(str(request.chat_builder_id))
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat builder not found"
        )
    
    await cb_service.configure_agents(
        str(request.chat_builder_id),
        [str(aid) for aid in request.agent_ids]
    )
    
    return {"message": "Chat builder configured successfully"}
