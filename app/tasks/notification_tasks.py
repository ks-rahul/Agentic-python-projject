"""Celery tasks for notifications."""
import asyncio
from celery import shared_task
from typing import List, Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_task(
    self,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    channels: List[str] = None,
    action_url: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None
):
    """Send notification asynchronously via Celery."""
    try:
        from app.services.notification_service import (
            notification_service, Notification, NotificationType, NotificationChannel
        )
        
        async def _send():
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=NotificationType(notification_type),
                channels=[NotificationChannel(c) for c in (channels or ["in_app"])],
                action_url=action_url,
                data=data or {},
                tenant_id=tenant_id
            )
            return await notification_service.send(notification)
        
        result = run_async(_send())
        logger.info("notification_task_completed", user_id=user_id, title=title, success=result)
        return result
        
    except Exception as e:
        logger.error("notification_task_failed", error=str(e), user_id=user_id, title=title)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_user_registered_task(self, user_id: str, name: str, email: str):
    """Send user registration notification asynchronously."""
    try:
        from app.services.notification_service import notification_service
        
        async def _send():
            return await notification_service.notify_user_registered(
                user_id=user_id,
                name=name,
                email=email
            )
        
        result = run_async(_send())
        logger.info("user_registered_notification_completed", user_id=user_id)
        return result
        
    except Exception as e:
        logger.error("user_registered_notification_failed", error=str(e), user_id=user_id)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_password_changed_task(self, user_id: str, email: str):
    """Send password changed notification asynchronously."""
    try:
        from app.services.notification_service import notification_service
        
        async def _send():
            return await notification_service.notify_password_changed(
                user_id=user_id,
                email=email
            )
        
        result = run_async(_send())
        logger.info("password_changed_notification_completed", user_id=user_id)
        return result
        
    except Exception as e:
        logger.error("password_changed_notification_failed", error=str(e), user_id=user_id)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_new_lead_task(
    self,
    user_id: str,
    lead_name: str,
    agent_name: str,
    tenant_id: Optional[str] = None
):
    """Send new lead notification asynchronously."""
    try:
        from app.services.notification_service import notification_service
        
        async def _send():
            return await notification_service.notify_new_lead(
                user_id=user_id,
                lead_name=lead_name,
                agent_name=agent_name,
                tenant_id=tenant_id
            )
        
        result = run_async(_send())
        logger.info("new_lead_notification_completed", user_id=user_id, lead_name=lead_name)
        return result
        
    except Exception as e:
        logger.error("new_lead_notification_failed", error=str(e), user_id=user_id)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_document_processed_task(
    self,
    user_id: str,
    doc_title: str,
    status: str,
    tenant_id: Optional[str] = None
):
    """Send document processed notification asynchronously."""
    try:
        from app.services.notification_service import notification_service
        
        async def _send():
            return await notification_service.notify_document_processed(
                user_id=user_id,
                doc_title=doc_title,
                status=status,
                tenant_id=tenant_id
            )
        
        result = run_async(_send())
        logger.info("document_processed_notification_completed", user_id=user_id, doc_title=doc_title)
        return result
        
    except Exception as e:
        logger.error("document_processed_notification_failed", error=str(e), user_id=user_id)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_agent_published_task(
    self,
    user_id: str,
    agent_name: str,
    tenant_id: Optional[str] = None
):
    """Send agent published notification asynchronously."""
    try:
        from app.services.notification_service import notification_service
        
        async def _send():
            return await notification_service.notify_agent_published(
                user_id=user_id,
                agent_name=agent_name,
                tenant_id=tenant_id
            )
        
        result = run_async(_send())
        logger.info("agent_published_notification_completed", user_id=user_id, agent_name=agent_name)
        return result
        
    except Exception as e:
        logger.error("agent_published_notification_failed", error=str(e), user_id=user_id)
        raise self.retry(exc=e)
