"""Document processing tasks for Celery."""
import asyncio
from typing import Dict, Any, List, Optional
from celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def process_document_task(
    self,
    file_path: str,
    document_id: str,
    tenant_id: str,
    knowledge_base_id: str,
    original_filename: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    custom_metadata: Optional[Dict[str, Any]] = None
):
    """Process and index a document into the vector store."""
    try:
        logger.info(f"Processing document {document_id} for tenant {tenant_id}")
        
        from app.services.document_indexing_service import get_indexing_service
        
        indexing_service = get_indexing_service()
        
        result = run_async(
            indexing_service.index_document(
                file_path=file_path,
                document_id=document_id,
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                original_filename=original_filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                custom_metadata=custom_metadata
            )
        )
        
        logger.info(f"Document {document_id} processed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True)
def delete_document_task(self, document_id: str, tenant_id: str):
    """Delete a document from the vector store."""
    try:
        logger.info(f"Deleting document {document_id} for tenant {tenant_id}")
        
        from app.services.document_indexing_service import get_indexing_service
        
        indexing_service = get_indexing_service()
        
        result = run_async(
            indexing_service.delete_document(
                document_id=document_id,
                tenant_id=tenant_id
            )
        )
        
        logger.info(f"Document {document_id} deleted: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        raise


@celery_app.task(bind=True)
def batch_delete_documents_task(self, tenant_id: str, document_ids: List[str]):
    """Batch delete documents from vector store."""
    try:
        logger.info(f"Batch deleting {len(document_ids)} documents for tenant {tenant_id}")
        
        from app.services.document_indexing_service import get_indexing_service
        
        indexing_service = get_indexing_service()
        
        results = []
        for doc_id in document_ids:
            result = run_async(
                indexing_service.delete_document(
                    document_id=doc_id,
                    tenant_id=tenant_id
                )
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        return {
            "status": "completed",
            "total": len(document_ids),
            "deleted_count": success_count,
            "failed_count": len(document_ids) - success_count
        }
        
    except Exception as e:
        logger.error(f"Error batch deleting documents: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, max_retries=3)
def process_batch_urls_task(
    self,
    tenant_id: str,
    knowledge_base_id: str,
    documents: List[Dict[str, Any]]
):
    """Process batch of documents from URLs."""
    try:
        logger.info(f"Processing {len(documents)} URLs for tenant {tenant_id}")
        
        import httpx
        import tempfile
        import os
        from pathlib import Path
        
        from app.services.document_indexing_service import get_indexing_service
        
        indexing_service = get_indexing_service()
        results = []
        
        for doc in documents:
            url = doc.get("url")
            document_id = doc.get("document_id")
            filename = doc.get("filename", url.split("/")[-1])
            
            try:
                # Download file
                with httpx.Client(timeout=60.0) as client:
                    response = client.get(url)
                    response.raise_for_status()
                
                # Save to temp file
                temp_dir = Path(tempfile.gettempdir()) / "agentic_downloads"
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / f"{document_id}_{filename}"
                
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                
                # Index the document
                result = run_async(
                    indexing_service.index_document(
                        file_path=str(temp_path),
                        document_id=document_id,
                        tenant_id=tenant_id,
                        knowledge_base_id=knowledge_base_id,
                        original_filename=filename
                    )
                )
                
                results.append({
                    "document_id": document_id,
                    "url": url,
                    **result
                })
                
                # Cleanup temp file
                os.remove(temp_path)
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")
                results.append({
                    "document_id": document_id,
                    "url": url,
                    "status": "error",
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        return {
            "status": "completed",
            "total": len(documents),
            "processed_count": success_count,
            "failed_count": len(documents) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch URLs: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def retrain_knowledge_base_task(
    self,
    tenant_id: str,
    knowledge_base_id: str,
    document_ids: List[str]
):
    """Retrain/reindex all documents in a knowledge base."""
    try:
        logger.info(f"Retraining knowledge base {knowledge_base_id} for tenant {tenant_id}")
        
        # This would typically:
        # 1. Delete existing vectors for the knowledge base
        # 2. Re-index all documents
        
        from app.services.document_indexing_service import get_indexing_service
        
        indexing_service = get_indexing_service()
        
        # Delete existing vectors for this knowledge base
        if indexing_service.pinecone_index:
            indexing_service.pinecone_index.delete(
                filter={"knowledge_base_id": {"$eq": knowledge_base_id}},
                namespace=tenant_id
            )
            logger.info(f"Deleted existing vectors for knowledge base {knowledge_base_id}")
        
        # Re-index would require fetching document file paths from database
        # This is a placeholder - actual implementation would query the database
        
        return {
            "status": "completed",
            "knowledge_base_id": knowledge_base_id,
            "message": "Knowledge base vectors cleared. Documents need to be re-indexed."
        }
        
    except Exception as e:
        logger.error(f"Error retraining knowledge base: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
