"""Website Scrape management routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from app.db.postgresql import get_db
from app.services.website_scrape_service import WebsiteScrapeService
from app.core.security import get_current_user

router = APIRouter()


class WebsiteScrapeCreate(BaseModel):
    knowledge_base_id: UUID
    title: str
    url: str
    scrape_type: Optional[str] = "single_url"
    include_paths: Optional[List[str]] = None
    exclude_paths: Optional[List[str]] = None
    max_pages: Optional[int] = 100
    max_depth: Optional[int] = 3


class WebsiteScrapeUpdate(BaseModel):
    title: Optional[str] = None
    include_paths: Optional[List[str]] = None
    exclude_paths: Optional[List[str]] = None
    max_pages: Optional[int] = None
    max_depth: Optional[int] = None


class WebsiteScrapeResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    tenant_id: UUID
    title: str
    url: str
    scrape_type: str
    status: str
    pages_scraped: int
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/list")
async def list_website_scrapes(
    knowledge_base_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all website scrapes."""
    scrape_service = WebsiteScrapeService(db)
    scrapes = await scrape_service.list_scrapes(
        tenant_id=current_user.get("tenant_id"),
        knowledge_base_id=str(knowledge_base_id) if knowledge_base_id else None
    )
    
    return {"website_scrapes": scrapes, "total": len(scrapes)}


@router.get("/get/{scrape_id}")
async def get_website_scrape(
    scrape_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get website scrape by ID."""
    scrape_service = WebsiteScrapeService(db)
    scrape = await scrape_service.get_by_id(str(scrape_id))
    
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    return scrape


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_website_scrape(
    request: WebsiteScrapeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new website scrape."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.create(
        knowledge_base_id=str(request.knowledge_base_id),
        tenant_id=current_user.get("tenant_id"),
        created_by=current_user["user_id"],
        title=request.title,
        url=request.url,
        scrape_type=request.scrape_type,
        include_paths=request.include_paths,
        exclude_paths=request.exclude_paths,
        max_pages=request.max_pages,
        max_depth=request.max_depth
    )
    
    return scrape


@router.post("/update/{scrape_id}")
async def update_website_scrape(
    scrape_id: UUID,
    request: WebsiteScrapeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update website scrape."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.get_by_id(str(scrape_id))
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    updated = await scrape_service.update(
        str(scrape_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated


@router.delete("/delete/{scrape_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website_scrape(
    scrape_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete website scrape."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.get_by_id(str(scrape_id))
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    await scrape_service.delete(str(scrape_id))
    return None


@router.post("/rescrape/{scrape_id}")
async def rescrape_website(
    scrape_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger rescraping of website."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.get_by_id(str(scrape_id))
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    result = await scrape_service.trigger_rescrape(str(scrape_id))
    return result


@router.post("/read-content")
async def read_scrape_content(
    scrape_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Read scraped content."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.get_by_id(str(scrape_id))
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    return {"content": scrape.scraped_content, "urls": scrape.discovered_urls}


@router.post("/stop-scrapping")
async def stop_scrapping(
    scrape_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Stop ongoing scraping task."""
    scrape_service = WebsiteScrapeService(db)
    
    scrape = await scrape_service.get_by_id(str(scrape_id))
    if not scrape:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website scrape not found"
        )
    
    result = await scrape_service.stop_scraping(str(scrape_id))
    return result
