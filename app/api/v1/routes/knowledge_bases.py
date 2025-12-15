"""Knowledge Base management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse,
    KnowledgeBaseListResponse, TrainedKnowledgeBaseResponse
)
from app.services.knowledge_base_service import KnowledgeBaseService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/list", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all knowledge bases for current tenant."""
    kb_service = KnowledgeBaseService(db)
    knowledge_bases = await kb_service.list_by_tenant(current_user.get("tenant_id"))
    
    return KnowledgeBaseListResponse(
        knowledge_bases=knowledge_bases,
        total=len(knowledge_bases)
    )


@router.get("/trained-knowledge", response_model=TrainedKnowledgeBaseResponse)
async def list_trained_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all trained knowledge bases."""
    kb_service = KnowledgeBaseService(db)
    knowledge_bases = await kb_service.list_trained(current_user.get("tenant_id"))
    
    return TrainedKnowledgeBaseResponse(
        knowledge_bases=knowledge_bases,
        total=len(knowledge_bases)
    )


@router.get("/get/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get knowledge base by ID."""
    kb_service = KnowledgeBaseService(db)
    kb = await kb_service.get_by_id(str(kb_id))
    
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    return kb


@router.post("/create", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new knowledge base."""
    kb_service = KnowledgeBaseService(db)
    
    kb = await kb_service.create(
        tenant_id=str(request.tenant_id),
        created_by=current_user["user_id"],
        title=request.title,
        short_description=request.short_description,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        max_response_tokens=request.max_response_tokens,
        retrieval_strategy=request.retrieval_strategy,
        retrieved_chunks=request.retrieved_chunks
    )
    
    return kb


@router.post("/update/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: UUID,
    request: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update knowledge base."""
    kb_service = KnowledgeBaseService(db)
    
    kb = await kb_service.get_by_id(str(kb_id))
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    updated_kb = await kb_service.update(
        str(kb_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_kb


@router.delete("/delete/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete knowledge base (soft delete)."""
    kb_service = KnowledgeBaseService(db)
    
    kb = await kb_service.get_by_id(str(kb_id))
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    await kb_service.delete(str(kb_id))
    return None


@router.get("/retrain/{kb_id}")
async def retrain_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger retraining of knowledge base."""
    kb_service = KnowledgeBaseService(db)
    
    kb = await kb_service.get_by_id(str(kb_id))
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Update status to training
    await kb_service.update(str(kb_id), training_status="training")
    
    # TODO: Trigger async retraining task
    
    return {"message": "Retraining initiated", "knowledge_base_id": str(kb_id)}
