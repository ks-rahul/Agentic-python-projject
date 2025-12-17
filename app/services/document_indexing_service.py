"""Document indexing service for RAG pipeline."""
import os
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import hashlib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class DocumentIndexingService:
    """Service for indexing documents into vector store."""
    
    def __init__(self):
        self._openai_client = None
        self._pinecone_index = None
        
        # Default chunking settings
        self.default_chunk_size = settings.DEFAULT_CHUNK_SIZE or 1000
        self.default_chunk_overlap = settings.DEFAULT_CHUNK_OVERLAP or 200
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None and OPENAI_AVAILABLE:
            api_key = settings.OPENAI_API_KEY
            if api_key:
                self._openai_client = AsyncOpenAI(api_key=api_key)
        return self._openai_client
    
    @property
    def pinecone_index(self):
        """Lazy load Pinecone index."""
        if self._pinecone_index is None and PINECONE_AVAILABLE:
            api_key = settings.PINECONE_API_KEY
            index_name = settings.PINECONE_INDEX_NAME
            if api_key and index_name:
                pc = Pinecone(api_key=api_key)
                self._pinecone_index = pc.Index(index_name)
        return self._pinecone_index
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")
        
        # Process in batches of 100
        all_embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.openai_client.embeddings.create(
                model=settings.EMBEDDING_MODEL or "text-embedding-3-small",
                input=batch
            )
            all_embeddings.extend([d.embedding for d in response.data])
        
        return all_embeddings
    
    def load_document(self, file_path: str) -> str:
        """Load document content from file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = path.suffix.lower()
        
        if extension == ".txt":
            return self._load_text(path)
        elif extension == ".pdf":
            return self._load_pdf(path)
        elif extension in [".docx", ".doc"]:
            return self._load_docx(path)
        elif extension == ".csv":
            return self._load_csv(path)
        elif extension in [".md", ".markdown"]:
            return self._load_text(path)
        elif extension == ".json":
            return self._load_json(path)
        else:
            # Try to load as text
            return self._load_text(path)
    
    def _load_text(self, path: Path) -> str:
        """Load text file."""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    
    def _load_pdf(self, path: Path) -> str:
        """Load PDF file."""
        if not PYPDF_AVAILABLE:
            raise ImportError("pypdf not installed. Install with: pip install pypdf")
        
        text = ""
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _load_docx(self, path: Path) -> str:
        """Load DOCX file."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        
        doc = docx.Document(path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    
    def _load_csv(self, path: Path) -> str:
        """Load CSV file as text."""
        import csv
        
        text = ""
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                text += ", ".join(row) + "\n"
        return text
    
    def _load_json(self, path: Path) -> str:
        """Load JSON file as text."""
        import json
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[str]:
        """Split text into chunks."""
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n", "\n\n"]:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
        
        return chunks
    
    async def index_document(
        self,
        file_path: str,
        document_id: str,
        tenant_id: str,
        knowledge_base_id: str,
        original_filename: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Index a document into the vector store."""
        logger.info(f"Starting indexing for document: {document_id}")
        
        try:
            # Load document
            content = self.load_document(file_path)
            
            if not content.strip():
                logger.warning(f"Empty content for document: {document_id}")
                return {
                    "status": "error",
                    "error": "Document has no content",
                    "chunks_indexed": 0
                }
            
            # Chunk the content
            chunks = self.chunk_text(content, chunk_size, chunk_overlap)
            logger.info(f"Document split into {len(chunks)} chunks")
            
            # Get embeddings
            embeddings = await self.get_embeddings(chunks)
            
            # Prepare vectors for Pinecone
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"{document_id}_{i}"
                
                metadata = {
                    "text": chunk[:8000],  # Pinecone metadata limit
                    "tenant_id": tenant_id,
                    "knowledge_base_id": knowledge_base_id,
                    "app_document_id": document_id,
                    "original_filename": original_filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "indexed_at": datetime.utcnow().isoformat(),
                }
                
                if custom_metadata:
                    metadata.update(custom_metadata)
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Upsert to Pinecone
            if self.pinecone_index:
                # Upsert in batches
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    self.pinecone_index.upsert(
                        vectors=batch,
                        namespace=tenant_id
                    )
                
                logger.info(f"Indexed {len(vectors)} vectors for document: {document_id}")
            else:
                logger.warning("Pinecone not configured, vectors not stored")
            
            # Call webhook to update document status
            await self._update_document_status(document_id, status=1)
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_indexed": len(chunks),
                "total_characters": len(content)
            }
            
        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}", exc_info=True)
            await self._update_document_status(document_id, status=-1)
            return {
                "status": "error",
                "error": str(e),
                "chunks_indexed": 0
            }
    
    async def delete_document(
        self,
        document_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Delete a document from the vector store."""
        logger.info(f"Deleting document from vector store: {document_id}")
        
        try:
            if self.pinecone_index:
                # Delete by filter
                self.pinecone_index.delete(
                    filter={"app_document_id": {"$eq": document_id}},
                    namespace=tenant_id
                )
                logger.info(f"Deleted vectors for document: {document_id}")
            
            return {
                "status": "success",
                "document_id": document_id
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _update_document_status(
        self,
        document_id: str,
        status: int
    ) -> None:
        """Update document status via webhook."""
        webhook_url = settings.DOCUMENT_STATUS_UPDATE_WEBHOOK_URL
        
        if not webhook_url:
            logger.debug("No webhook URL configured for document status updates")
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook_url,
                    data={
                        "document_id": document_id,
                        "status": status
                    },
                    timeout=10.0
                )
                logger.info(f"Document status updated: {document_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")


# Singleton instance
_indexing_service = None

def get_indexing_service() -> DocumentIndexingService:
    """Get document indexing service singleton."""
    global _indexing_service
    if _indexing_service is None:
        _indexing_service = DocumentIndexingService()
    return _indexing_service
