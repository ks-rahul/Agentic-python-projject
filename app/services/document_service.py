"""Document service."""
from typing import Optional, List, Dict, Any
import os
import uuid
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.base_service import BaseService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService(BaseService[Document]):
    """Service for document operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Document)
    
    async def list_documents(
        self,
        tenant_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None
    ) -> List[Document]:
        """List documents with optional filtering."""
        query = select(Document).where(Document.deleted_at.is_(None))
        
        if knowledge_base_id:
            query = query.where(Document.knowledge_base_id == knowledge_base_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_from_upload(
        self,
        knowledge_base_id: str,
        created_by: str,
        title: str,
        file: UploadFile,
        custom_metadata: str = "{}",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create document from file upload."""
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Determine file type
        file_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
        
        # Save file
        upload_dir = os.path.join(settings.STORAGE_PATH, knowledge_base_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{doc_id}.{file_ext}")
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create document record
        document = await self.create(
            id=doc_id,
            knowledge_base_id=knowledge_base_id,
            created_by=created_by,
            title=title,
            original_name=file.filename,
            type=file_ext,
            source_type="upload",
            document=file_path,
            status="pending"
        )
        
        # TODO: Trigger async indexing task
        
        return {
            "document_id": document.id,
            "filename": file.filename,
            "nodes_indexed": 1
        }
    
    async def batch_delete(
        self,
        document_ids: List[str],
        tenant_id: str
    ) -> str:
        """Batch delete documents."""
        # TODO: Implement Celery task for batch deletion
        task_id = str(uuid.uuid4())
        
        for doc_id in document_ids:
            await self.delete(doc_id)
        
        return task_id
