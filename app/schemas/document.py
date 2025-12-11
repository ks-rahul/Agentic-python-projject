"""Document schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DocumentBase(BaseModel):
    title: str
    type: Optional[str] = None
    source_type: Optional[str] = "upload"


class DocumentCreate(DocumentBase):
    knowledge_base_id: UUID


class DocumentUpdate(BaseModel):
    title: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: UUID
    knowledge_base_id: UUID
    created_by: Optional[UUID] = None
    original_name: Optional[str] = None
    document: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: UUID
    filename: str
    nodes_indexed: int


class BatchUrlUploadItem(BaseModel):
    document_id: str
    url: str
    title: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None


class BatchDeleteRequest(BaseModel):
    document_ids: List[str]


class BatchInitiatedResponse(BaseModel):
    message: str
    task_id: str
    tenant_id: str
    document_count: int
