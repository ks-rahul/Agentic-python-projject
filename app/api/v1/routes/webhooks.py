"""Webhook routes for external integrations."""
from fastapi import APIRouter, Request, Query, Response, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/document-status-update")
async def document_status_update(request: Request):
    """Handle document status update webhook from RAG service."""
    try:
        data = await request.json()
        logger.info(f"Document status update received: {data}")
        
        # TODO: Update document status in database
        document_id = data.get("document_id")
        status = data.get("status")
        
        return {"success": True, "message": "Status updated"}
    except Exception as e:
        logger.error(f"Error processing document status update: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/website-scrape-update")
async def website_scrape_update(request: Request):
    """Handle website scrape data webhook."""
    try:
        data = await request.json()
        logger.info(f"Website scrape update received: {data}")
        
        # TODO: Process scraped data and create documents
        
        return {"success": True, "message": "Scrape data processed"}
    except Exception as e:
        logger.error(f"Error processing website scrape update: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/website-scrape-sitemap-urls")
async def website_scrape_sitemap_urls(request: Request):
    """Handle discovered sitemap URLs webhook."""
    try:
        data = await request.json()
        logger.info(f"Sitemap URLs discovered: {data}")
        
        # TODO: Store discovered URLs
        
        return {"success": True, "message": "URLs stored"}
    except Exception as e:
        logger.error(f"Error processing sitemap URLs: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


# WhatsApp webhook endpoints
@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_token: str = Query(None, alias="hub.verify_token")
):
    """WhatsApp webhook verification endpoint."""
    if hub_mode == "subscribe" and hub_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    else:
        logger.warning("WhatsApp webhook verification failed")
        return Response(content="Verification failed", status_code=403)


@router.post("/whatsapp")
async def whatsapp_webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks
):
    """WhatsApp webhook message receiver."""
    try:
        data = await request.json()
        
        if data and data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        phone_number_id = value.get("metadata", {}).get("phone_number_id")
                        
                        for message in value.get("messages", []):
                            if message.get("type") == "text":
                                from_number = message.get("from")
                                text_content = message.get("text", {}).get("body")
                                message_id = message.get("id")
                                
                                logger.info(
                                    f"WhatsApp message received: {message_id} from {from_number}"
                                )
                                
                                # TODO: Process message in background
                                # background_tasks.add_task(
                                #     process_whatsapp_message,
                                #     data, phone_number_id
                                # )
                                
                                return JSONResponse(
                                    content={
                                        "status": "processing",
                                        "message_id": message_id
                                    },
                                    status_code=200
                                )
        
        return JSONResponse(content={"status": "success"}, status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=200  # Return 200 to prevent retries
        )
