"""Notification service for in-app, push, and webhook notifications."""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import json
import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_redis
from app.services.email_service import email_service

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"
    SMS = "sms"


class Notification:
    """Notification data model."""
    
    def __init__(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        channels: List[NotificationChannel] = None,
        data: Dict[str, Any] = None,
        action_url: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        self.id = f"notif_{datetime.now(timezone.utc).timestamp()}"
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.title = title
        self.message = message
        self.type = notification_type
        self.channels = channels or [NotificationChannel.IN_APP]
        self.data = data or {}
        self.action_url = action_url
        self.created_at = datetime.now(timezone.utc)
        self.read_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "message": self.message,
            "type": self.type.value,
            "channels": [c.value for c in self.channels],
            "data": self.data,
            "action_url": self.action_url,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None
        }


class NotificationService:
    """Service for managing and sending notifications."""
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if not self.redis:
            self.redis = await get_redis()
        return self.redis
    
    async def send(self, notification: Notification) -> bool:
        """Send notification through configured channels."""
        success = True
        
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    await self._send_in_app(notification)
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email(notification)
                elif channel == NotificationChannel.PUSH:
                    await self._send_push(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(notification)
                elif channel == NotificationChannel.SMS:
                    await self._send_sms(notification)
                    
                logger.info(
                    "notification_sent",
                    channel=channel.value,
                    user_id=notification.user_id,
                    type=notification.type.value
                )
            except Exception as e:
                logger.error(
                    "notification_failed",
                    channel=channel.value,
                    user_id=notification.user_id,
                    error=str(e)
                )
                success = False
        
        return success
    
    async def _send_in_app(self, notification: Notification):
        """Store notification in Redis for in-app display."""
        redis = await self._get_redis()
        key = f"notifications:{notification.user_id}"
        
        await redis.lpush(key, json.dumps(notification.to_dict()))
        await redis.ltrim(key, 0, 99)  # Keep last 100 notifications
        await redis.expire(key, 60 * 60 * 24 * 30)  # 30 days TTL
        
        # Publish for real-time updates
        await redis.publish(
            f"notifications:{notification.user_id}",
            json.dumps(notification.to_dict())
        )
    
    async def _send_email(self, notification: Notification):
        """Send notification via email."""
        # Get user email from notification data or fetch from DB
        email = notification.data.get("email")
        if not email:
            logger.warning("email_notification_skipped", reason="no_email", user_id=notification.user_id)
            return
        
        await email_service.send_template_email(
            to=[email],
            subject=notification.title,
            template_name="notification",
            context={
                "title": notification.title,
                "message": notification.message,
                "action_url": notification.action_url,
                "action_text": notification.data.get("action_text")
            }
        )
    
    async def _send_push(self, notification: Notification):
        """Send push notification (Firebase/OneSignal)."""
        push_token = notification.data.get("push_token")
        if not push_token:
            logger.warning("push_notification_skipped", reason="no_token", user_id=notification.user_id)
            return
        
        # Firebase Cloud Messaging
        fcm_key = getattr(settings, 'FCM_SERVER_KEY', None)
        if fcm_key:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json={
                        "to": push_token,
                        "notification": {
                            "title": notification.title,
                            "body": notification.message
                        },
                        "data": notification.data
                    },
                    headers={"Authorization": f"key={fcm_key}"}
                )
    
    async def _send_webhook(self, notification: Notification):
        """Send notification to webhook URL."""
        webhook_url = notification.data.get("webhook_url")
        if not webhook_url:
            logger.warning("webhook_notification_skipped", reason="no_url", user_id=notification.user_id)
            return
        
        async with httpx.AsyncClient() as client:
            await client.post(
                webhook_url,
                json=notification.to_dict(),
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
    
    async def _send_sms(self, notification: Notification):
        """Send SMS notification (Twilio)."""
        phone = notification.data.get("phone")
        if not phone:
            logger.warning("sms_notification_skipped", reason="no_phone", user_id=notification.user_id)
            return
        
        # Twilio integration
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_from = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if twilio_sid and twilio_token and twilio_from:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                    data={
                        "To": phone,
                        "From": twilio_from,
                        "Body": f"{notification.title}: {notification.message}"
                    },
                    auth=(twilio_sid, twilio_token)
                )

    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        redis = await self._get_redis()
        key = f"notifications:{user_id}"
        
        notifications = await redis.lrange(key, offset, offset + limit - 1)
        result = []
        
        for notif_json in notifications:
            notif = json.loads(notif_json)
            if unread_only and notif.get("read_at"):
                continue
            result.append(notif)
        
        return result
    
    async def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read."""
        redis = await self._get_redis()
        key = f"notifications:{user_id}"
        
        notifications = await redis.lrange(key, 0, -1)
        
        for i, notif_json in enumerate(notifications):
            notif = json.loads(notif_json)
            if notif["id"] == notification_id:
                notif["read_at"] = datetime.now(timezone.utc).isoformat()
                await redis.lset(key, i, json.dumps(notif))
                return True
        
        return False
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        redis = await self._get_redis()
        key = f"notifications:{user_id}"
        
        notifications = await redis.lrange(key, 0, -1)
        count = 0
        
        for i, notif_json in enumerate(notifications):
            notif = json.loads(notif_json)
            if not notif.get("read_at"):
                notif["read_at"] = datetime.now(timezone.utc).isoformat()
                await redis.lset(key, i, json.dumps(notif))
                count += 1
        
        return count
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        redis = await self._get_redis()
        key = f"notifications:{user_id}"
        
        notifications = await redis.lrange(key, 0, -1)
        count = 0
        
        for notif_json in notifications:
            notif = json.loads(notif_json)
            if not notif.get("read_at"):
                count += 1
        
        return count
    
    async def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification."""
        redis = await self._get_redis()
        key = f"notifications:{user_id}"
        
        notifications = await redis.lrange(key, 0, -1)
        
        for notif_json in notifications:
            notif = json.loads(notif_json)
            if notif["id"] == notification_id:
                await redis.lrem(key, 1, notif_json)
                return True
        
        return False
    
    # Convenience methods for common notifications
    async def notify_user_registered(self, user_id: str, name: str, email: str):
        """Send welcome notification."""
        notification = Notification(
            user_id=user_id,
            title="Welcome!",
            message=f"Welcome to {settings.APP_NAME}, {name}! Your account is ready.",
            notification_type=NotificationType.SUCCESS,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            data={"email": email}
        )
        await self.send(notification)
    
    async def notify_password_changed(self, user_id: str, email: str):
        """Notify user of password change."""
        notification = Notification(
            user_id=user_id,
            title="Password Changed",
            message="Your password has been successfully changed. If you didn't do this, please contact support.",
            notification_type=NotificationType.WARNING,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            data={"email": email}
        )
        await self.send(notification)
    
    async def notify_new_lead(self, user_id: str, lead_name: str, agent_name: str, tenant_id: str = None):
        """Notify about new lead capture."""
        notification = Notification(
            user_id=user_id,
            title="New Lead Captured",
            message=f"New lead '{lead_name}' captured by agent '{agent_name}'",
            notification_type=NotificationType.INFO,
            channels=[NotificationChannel.IN_APP],
            tenant_id=tenant_id,
            action_url=f"{settings.APP_URL}/leads"
        )
        await self.send(notification)
    
    async def notify_document_processed(self, user_id: str, doc_title: str, status: str, tenant_id: str = None):
        """Notify about document processing completion."""
        notification = Notification(
            user_id=user_id,
            title="Document Processed",
            message=f"Document '{doc_title}' has been {status}",
            notification_type=NotificationType.SUCCESS if status == "completed" else NotificationType.ERROR,
            channels=[NotificationChannel.IN_APP],
            tenant_id=tenant_id
        )
        await self.send(notification)
    
    async def notify_agent_published(self, user_id: str, agent_name: str, tenant_id: str = None):
        """Notify about agent publication."""
        notification = Notification(
            user_id=user_id,
            title="Agent Published",
            message=f"Agent '{agent_name}' is now live and ready to chat!",
            notification_type=NotificationType.SUCCESS,
            channels=[NotificationChannel.IN_APP],
            tenant_id=tenant_id
        )
        await self.send(notification)


# Singleton instance
notification_service = NotificationService()
