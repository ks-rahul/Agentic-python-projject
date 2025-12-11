"""Website Scrape service."""
from typing import Optional, List, Dict, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.website_scrape import WebsiteScrape
from app.services.base_service import BaseService


class WebsiteScrapeService(BaseService[WebsiteScrape]):
    """Service for website scrape operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, WebsiteScrape)
    
    async def list_scrapes(
        self,
        tenant_id: str,
        knowledge_base_id: Optional[str] = None
    ) -> List[WebsiteScrape]:
        """List website scrapes."""
        query = (
            select(WebsiteScrape)
            .where(WebsiteScrape.tenant_id == tenant_id)
            .where(WebsiteScrape.deleted_at.is_(None))
        )
        
        if knowledge_base_id:
            query = query.where(WebsiteScrape.knowledge_base_id == knowledge_base_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def trigger_rescrape(self, scrape_id: str) -> Dict[str, Any]:
        """Trigger rescraping."""
        scrape = await self.get_by_id(scrape_id)
        if not scrape:
            raise ValueError("Scrape not found")
        
        # Update status
        await self.update(scrape_id, status="pending")
        
        # TODO: Trigger Celery task
        task_id = str(uuid.uuid4())
        await self.update(scrape_id, scrape_task_id=task_id)
        
        return {
            "message": "Rescrape initiated",
            "task_id": task_id,
            "scrape_id": scrape_id
        }
    
    async def stop_scraping(self, scrape_id: str) -> Dict[str, Any]:
        """Stop ongoing scraping."""
        scrape = await self.get_by_id(scrape_id)
        if not scrape:
            raise ValueError("Scrape not found")
        
        # TODO: Cancel Celery task
        await self.update(scrape_id, status="stopped")
        
        return {
            "message": "Scraping stopped",
            "scrape_id": scrape_id
        }
