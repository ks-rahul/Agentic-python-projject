"""Web scraping tasks for Celery."""
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import re
from celery_app import celery_app
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def fetch_url(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch URL content."""
    import httpx
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AgenticBot/1.0)"
        })
        response.raise_for_status()
        return {
            "content": response.text,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "url": str(response.url)
        }


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML."""
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        
        return text
        
    except ImportError:
        logger.warning("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
        # Fallback: basic HTML tag removal
        clean = re.sub(r'<[^>]+>', ' ', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """Extract links from HTML."""
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            # Only include http/https URLs
            if full_url.startswith(("http://", "https://")):
                links.append(full_url)
        
        return list(set(links))
        
    except ImportError:
        return []


def parse_sitemap(xml_content: str) -> List[str]:
    """Parse sitemap XML and extract URLs."""
    try:
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(xml_content)
        
        # Handle different sitemap formats
        namespaces = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9"
        }
        
        urls = []
        
        # Try standard sitemap format
        for url in root.findall(".//sm:url/sm:loc", namespaces):
            if url.text:
                urls.append(url.text)
        
        # Try sitemap index format
        for sitemap in root.findall(".//sm:sitemap/sm:loc", namespaces):
            if sitemap.text:
                urls.append(sitemap.text)
        
        # Fallback: try without namespace
        if not urls:
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    urls.append(loc.text)
        
        return urls
        
    except Exception as e:
        logger.error(f"Error parsing sitemap: {e}")
        return []


async def update_scrape_status(
    scrape_id: str,
    status: str,
    content: Optional[str] = None,
    discovered_urls: Optional[List[str]] = None,
    error_message: Optional[str] = None
):
    """Update scrape status via webhook or database."""
    webhook_url = settings.DOCUMENT_STATUS_UPDATE_WEBHOOK_URL
    
    if webhook_url:
        try:
            import httpx
            
            # Use website scrape webhook endpoint
            scrape_webhook = webhook_url.replace("document-status-update", "website-scrape-update")
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    scrape_webhook,
                    json={
                        "scrape_id": scrape_id,
                        "status": status,
                        "scraped_content": content,
                        "discovered_urls": discovered_urls,
                        "error_message": error_message
                    },
                    timeout=10.0
                )
        except Exception as e:
            logger.error(f"Failed to update scrape status: {e}")


@celery_app.task(bind=True, max_retries=3)
def scrape_url_task(
    self,
    url: str,
    scrape_id: str,
    tenant_id: str,
    knowledge_base_id: Optional[str] = None,
    extract_links: bool = False,
    max_depth: int = 1,
    current_depth: int = 0
):
    """Scrape a single URL and optionally extract links."""
    try:
        logger.info(f"Scraping URL: {url} (depth: {current_depth})")
        
        # Fetch the URL
        result = run_async(fetch_url(url))
        
        # Extract text content
        content = extract_text_from_html(result["content"])
        
        # Extract links if requested
        discovered_urls = []
        if extract_links and current_depth < max_depth:
            discovered_urls = extract_links_from_html(result["content"], url)
            # Filter to same domain
            base_domain = urlparse(url).netloc
            discovered_urls = [
                u for u in discovered_urls 
                if urlparse(u).netloc == base_domain
            ][:100]  # Limit to 100 URLs
        
        # Update status
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="completed",
            content=content,
            discovered_urls=discovered_urls
        ))
        
        # If we have a knowledge base, index the content
        if knowledge_base_id and content:
            from app.tasks.document_tasks import process_document_task
            import tempfile
            import os
            from pathlib import Path
            
            # Save content to temp file
            temp_dir = Path(tempfile.gettempdir()) / "agentic_scrapes"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / f"{scrape_id}.txt"
            
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Queue document processing
            process_document_task.delay(
                file_path=str(temp_path),
                document_id=scrape_id,
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                original_filename=url
            )
        
        logger.info(f"Successfully scraped URL: {url}")
        
        return {
            "status": "completed",
            "url": url,
            "content_length": len(content),
            "discovered_urls_count": len(discovered_urls)
        }
        
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}", exc_info=True)
        
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="failed",
            error_message=str(e)
        ))
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_sitemap_task(
    self,
    sitemap_url: str,
    scrape_id: str,
    tenant_id: str,
    knowledge_base_id: Optional[str] = None,
    max_pages: int = 100,
    include_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None
):
    """Scrape URLs from a sitemap."""
    try:
        logger.info(f"Scraping sitemap: {sitemap_url}")
        
        # Fetch sitemap
        result = run_async(fetch_url(sitemap_url))
        
        # Parse sitemap
        urls = parse_sitemap(result["content"])
        
        # Filter URLs
        if include_paths:
            urls = [u for u in urls if any(p in u for p in include_paths)]
        if exclude_paths:
            urls = [u for u in urls if not any(p in u for p in exclude_paths)]
        
        # Limit URLs
        urls = urls[:max_pages]
        
        logger.info(f"Found {len(urls)} URLs in sitemap")
        
        # Update with discovered URLs
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="processing",
            discovered_urls=urls
        ))
        
        # Queue scraping for each URL
        for i, url in enumerate(urls):
            child_scrape_id = f"{scrape_id}_page_{i}"
            scrape_url_task.delay(
                url=url,
                scrape_id=child_scrape_id,
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                extract_links=False
            )
        
        return {
            "status": "completed",
            "sitemap_url": sitemap_url,
            "urls_found": len(urls),
            "urls_queued": len(urls)
        }
        
    except Exception as e:
        logger.error(f"Error scraping sitemap {sitemap_url}: {e}", exc_info=True)
        
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="failed",
            error_message=str(e)
        ))
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def scrape_website_task(
    self,
    start_url: str,
    scrape_id: str,
    tenant_id: str,
    knowledge_base_id: Optional[str] = None,
    max_pages: int = 100,
    max_depth: int = 3,
    include_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None
):
    """Crawl a website starting from a URL."""
    try:
        logger.info(f"Starting website crawl: {start_url}")
        
        visited = set()
        to_visit = [(start_url, 0)]  # (url, depth)
        scraped_count = 0
        
        base_domain = urlparse(start_url).netloc
        
        while to_visit and scraped_count < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            # Apply path filters
            if include_paths and not any(p in url for p in include_paths):
                continue
            if exclude_paths and any(p in url for p in exclude_paths):
                continue
            
            visited.add(url)
            
            try:
                # Fetch and process URL
                result = run_async(fetch_url(url))
                content = extract_text_from_html(result["content"])
                
                # Extract links for further crawling
                if depth < max_depth:
                    links = extract_links_from_html(result["content"], url)
                    for link in links:
                        if urlparse(link).netloc == base_domain and link not in visited:
                            to_visit.append((link, depth + 1))
                
                # Index content if knowledge base provided
                if knowledge_base_id and content:
                    child_scrape_id = f"{scrape_id}_page_{scraped_count}"
                    
                    from app.tasks.document_tasks import process_document_task
                    import tempfile
                    from pathlib import Path
                    
                    temp_dir = Path(tempfile.gettempdir()) / "agentic_scrapes"
                    temp_dir.mkdir(exist_ok=True)
                    temp_path = temp_dir / f"{child_scrape_id}.txt"
                    
                    with open(temp_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    process_document_task.delay(
                        file_path=str(temp_path),
                        document_id=child_scrape_id,
                        tenant_id=tenant_id,
                        knowledge_base_id=knowledge_base_id,
                        original_filename=url
                    )
                
                scraped_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        # Update final status
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="completed",
            discovered_urls=list(visited)
        ))
        
        logger.info(f"Website crawl completed: {scraped_count} pages scraped")
        
        return {
            "status": "completed",
            "start_url": start_url,
            "pages_scraped": scraped_count,
            "pages_discovered": len(visited)
        }
        
    except Exception as e:
        logger.error(f"Error crawling website {start_url}: {e}", exc_info=True)
        
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="failed",
            error_message=str(e)
        ))
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True)
def scrape_table_task(
    self,
    url: str,
    table_selector: str,
    tenant_id: str,
    scrape_id: Optional[str] = None
):
    """Scrape table data from a URL."""
    try:
        logger.info(f"Scraping table from: {url}")
        
        from bs4 import BeautifulSoup
        
        # Fetch the URL
        result = run_async(fetch_url(url))
        soup = BeautifulSoup(result["content"], "html.parser")
        
        # Find table
        table = soup.select_one(table_selector) if table_selector else soup.find("table")
        
        if not table:
            return {
                "status": "error",
                "error": "No table found",
                "url": url
            }
        
        # Extract headers
        headers = []
        header_row = table.find("tr")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        
        # Extract rows
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header row
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                if headers:
                    row_dict = dict(zip(headers, cells))
                    rows.append(row_dict)
                else:
                    rows.append(cells)
        
        logger.info(f"Extracted {len(rows)} rows from table")
        
        return {
            "status": "completed",
            "url": url,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows)
        }
        
    except ImportError:
        logger.error("BeautifulSoup not installed")
        return {
            "status": "error",
            "error": "BeautifulSoup not installed",
            "url": url
        }
    except Exception as e:
        logger.error(f"Error scraping table from {url}: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "url": url
        }


@celery_app.task(bind=True)
def stop_scraping_task(self, scrape_id: str, tenant_id: str):
    """Stop an ongoing scraping task."""
    try:
        logger.info(f"Stopping scrape task: {scrape_id}")
        
        # Update status to stopped
        run_async(update_scrape_status(
            scrape_id=scrape_id,
            status="stopped"
        ))
        
        # In a production system, you would also:
        # 1. Revoke any pending child tasks
        # 2. Clean up any temporary files
        
        return {
            "status": "stopped",
            "scrape_id": scrape_id
        }
        
    except Exception as e:
        logger.error(f"Error stopping scrape task: {e}")
        raise
