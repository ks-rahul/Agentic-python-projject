"""Knowledge Base schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class KnowledgeBaseBase(BaseModel):
    title: str
    short_description: Optional[str] = None
    chunk_size: Optional[int] = 1000
    chunk_overlap: Optional[int] = 200
    max_response_tokens: Optional[int] = 2048
    retrieval_strategy: Optional[str] = "similarity"
    retrieved_chunks: Optional[int] = 5


class KnowledgeBaseCreate(KnowledgeBaseBase):
    tenant_id: UUID


class KnowledgeBaseUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    max_response_tokens: Optional[int] = None
    retrieval_strategy: Optional[str] = None
    retrieved_chunks: Optional[int] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: UUID
    tenant_id: UUID
    created_by: Optional[UUID] = None
    status: str
    training_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    knowledge_bases: List[KnowledgeBaseResponse]
    total: int


class TrainedKnowledgeBaseResponse(BaseModel):
    knowledge_bases: List[KnowledgeBaseResponse]
    total: int
