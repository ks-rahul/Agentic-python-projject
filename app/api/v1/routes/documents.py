"""Document management routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse,
    DocumentUploadResponse, BatchDeleteRequest, BatchInitiatedResponse
)
from app.services.document_service import DocumentService
from app.core.security import get_current_user

router = APIRouter()


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    knowledge_base_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all documents."""
    doc_service = DocumentService(db)
    documents = await doc_service.list_documents(
        tenant_id=current_user.get("tenant_id"),
        knowledge_base_id=str(knowledge_base_id) if knowledge_base_id else None
    )
    
    return DocumentListResponse(
        documents=documents,
        total=len(documents)
    )


@router.get("/get/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get document by ID."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_by_id(str(doc_id))
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return doc


@router.post("/create", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    knowledge_base_id: UUID = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    custom_metadata: Optional[str] = Form("{}"),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upload and create a new document."""
    doc_service = DocumentService(db)
    
    result = await doc_service.create_from_upload(
        knowledge_base_id=str(knowledge_base_id),
        created_by=current_user["user_id"],
        title=title,
        file=file,
        custom_metadata=custom_metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    return DocumentUploadResponse(
        message="Document uploaded and indexed successfully",
        document_id=result["document_id"],
        filename=result["filename"],
        nodes_indexed=result.get("nodes_indexed", 1)
    )


@router.post("/update/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: UUID,
    request: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update document."""
    doc_service = DocumentService(db)
    
    doc = await doc_service.get_by_id(str(doc_id))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    updated_doc = await doc_service.update(
        str(doc_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_doc


@router.delete("/delete/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete document (soft delete)."""
    doc_service = DocumentService(db)
    
    doc = await doc_service.get_by_id(str(doc_id))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    await doc_service.delete(str(doc_id))
    return None


@router.delete("/batch", response_model=BatchInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_delete_documents(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Batch delete documents."""
    if not request.document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document IDs provided"
        )
    
    if len(request.document_ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 documents per batch"
        )
    
    doc_service = DocumentService(db)
    task_id = await doc_service.batch_delete(
        document_ids=request.document_ids,
        tenant_id=current_user.get("tenant_id")
    )
    
    return BatchInitiatedResponse(
        message="Batch deletion initiated",
        task_id=task_id,
        tenant_id=current_user.get("tenant_id"),
        document_count=len(request.document_ids)
    )


# Batch URL Processing Models
from pydantic import BaseModel, HttpUrl
from typing import List


class BatchUrlUploadItem(BaseModel):
    """Single URL item for batch processing."""
    url: str
    title: Optional[str] = None
    document_id: Optional[str] = None
    custom_metadata: Optional[dict] = {}


class BatchUrlUploadRequest(BaseModel):
    """Request for batch URL document processing."""
    knowledge_base_id: UUID
    documents: List[BatchUrlUploadItem]
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


@router.post("/from-url/batch", response_model=BatchInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_process_documents_from_url(
    request: BatchUrlUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Accepts a batch of documents from URLs and initiates a background
    task to process all of them. This endpoint returns immediately.
    """
    if not request.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body cannot be an empty list"
        )
    
    if len(request.documents) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 URLs per batch"
        )
    
    doc_service = DocumentService(db)
    
    # Dispatch Celery task for batch URL processing
    task_id = await doc_service.batch_process_urls(
        knowledge_base_id=str(request.knowledge_base_id),
        tenant_id=current_user.get("tenant_id"),
        documents=[doc.model_dump() for doc in request.documents],
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap
    )
    
    return BatchInitiatedResponse(
        message="Batch URL processing initiated. Documents will be processed in the background.",
        task_id=task_id,
        tenant_id=current_user.get("tenant_id"),
        document_count=len(request.documents)
    )


@router.post("/from-url", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_document_from_url(
    knowledge_base_id: UUID = Form(...),
    url: str = Form(...),
    title: Optional[str] = Form(None),
    custom_metadata: Optional[str] = Form("{}"),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a document from a URL."""
    import json
    
    doc_service = DocumentService(db)
    
    try:
        metadata = json.loads(custom_metadata) if custom_metadata else {}
    except json.JSONDecodeError:
        metadata = {}
    
    result = await doc_service.create_from_url(
        knowledge_base_id=str(knowledge_base_id),
        tenant_id=current_user.get("tenant_id"),
        created_by=current_user["user_id"],
        url=url,
        title=title,
        custom_metadata=metadata,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    return DocumentUploadResponse(
        message="Document created from URL successfully",
        document_id=result["document_id"],
        filename=result.get("filename", url),
        nodes_indexed=result.get("nodes_indexed", 1)
    )
