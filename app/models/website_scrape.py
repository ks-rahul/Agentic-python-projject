"""Website Scrape model."""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, SoftDeleteMixin


class ScrapeStatus(str, enum.Enum):
    PENDING = "pending"
    SCRAPING = "scraping"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ScrapeType(str, enum.Enum):
    SINGLE_URL = "single_url"
    SITEMAP = "sitemap"
    CRAWL = "crawl"


class WebsiteScrape(BaseModel, SoftDeleteMixin):
    """Website scrape configuration and status."""
    __tablename__ = "website_scrapes"

    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("website_scrapes.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    scrape_type = Column(Enum(ScrapeType), default=ScrapeType.SINGLE_URL)
    status = Column(Enum(ScrapeStatus), default=ScrapeStatus.PENDING)
    
    # Scraping configuration
    include_paths = Column(JSON, nullable=True)
    exclude_paths = Column(JSON, nullable=True)
    max_pages = Column(Integer, default=100)
    max_depth = Column(Integer, default=3)
    
    # Results
    scraped_content = Column(Text, nullable=True)
    discovered_urls = Column(JSON, nullable=True)
    pages_scraped = Column(Integer, default=0)
    
    # Task tracking
    scrape_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="website_scrapes")
    children = relationship("WebsiteScrape", backref="parent", remote_side="WebsiteScrape.id")
