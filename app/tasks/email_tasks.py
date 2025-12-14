"""Celery tasks for email sending."""
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(
    self,
    to: List[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
):
    """Send email asynchronously via Celery."""
    try:
        from app.services.email_service import email_service
        
        async def _send():
            return await email_service.send_email(
                to=to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=from_email,
                from_name=from_name
            )
        
        result = run_async(_send())
        logger.info("email_task_completed", to=to, subject=subject, success=result)
        return result
        
    except Exception as e:
        logger.error("email_task_failed", error=str(e), to=to, subject=subject)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, email: str, name: str, verification_url: str):
    """Send verification email asynchronously."""
    try:
        from app.services.email_service import email_service
        
        async def _send():
            return await email_service.send_verification_email(
                email=email,
                name=name,
                verification_url=verification_url
            )
        
        result = run_async(_send())
        logger.info("verification_email_task_completed", email=email, success=result)
        return result
        
    except Exception as e:
        logger.error("verification_email_task_failed", error=str(e), email=email)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, email: str, name: str, reset_url: str):
    """Send password reset email asynchronously."""
    try:
        from app.services.email_service import email_service
        
        async def _send():
            return await email_service.send_password_reset_email(
                email=email,
                name=name,
                reset_url=reset_url
            )
        
        result = run_async(_send())
        logger.info("password_reset_email_task_completed", email=email, success=result)
        return result
        
    except Exception as e:
        logger.error("password_reset_email_task_failed", error=str(e), email=email)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, email: str, name: str):
    """Send welcome email asynchronously."""
    try:
        from app.services.email_service import email_service
        
        async def _send():
            return await email_service.send_welcome_email(email=email, name=name)
        
        result = run_async(_send())
        logger.info("welcome_email_task_completed", email=email, success=result)
        return result
        
    except Exception as e:
        logger.error("welcome_email_task_failed", error=str(e), email=email)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_template_email_task(
    self,
    to: List[str],
    subject: str,
    template_name: str,
    context: Dict[str, Any]
):
    """Send template email asynchronously."""
    try:
        from app.services.email_service import email_service
        
        async def _send():
            return await email_service.send_template_email(
                to=to,
                subject=subject,
                template_name=template_name,
                context=context
            )
        
        result = run_async(_send())
        logger.info("template_email_task_completed", to=to, template=template_name, success=result)
        return result
        
    except Exception as e:
        logger.error("template_email_task_failed", error=str(e), to=to, template=template_name)
        raise self.retry(exc=e)
