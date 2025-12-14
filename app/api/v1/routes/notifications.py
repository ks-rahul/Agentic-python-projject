"""Notification routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.notification_service import notification_service, Notification, NotificationType, NotificationChannel
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str
    title: str
    message: str
    type: str
    action_url: Optional[str] = None
    created_at: str
    read_at: Optional[str] = None


class NotificationListResponse(BaseModel):
    """Notification list response."""
    notifications: list
    unread_count: int


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    user_id: str
    title: str
    message: str
    type: str = "info"
    channels: list = ["in_app"]
    action_url: Optional[str] = None
    data: Optional[dict] = None


@router.get("/list", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """List notifications for current user."""
    user_id = current_user.get("sub")
    
    notifications = await notification_service.get_user_notifications(
        user_id=user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only
    )
    
    unread_count = await notification_service.get_unread_count(user_id)
    
    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count
    )


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get unread notification count."""
    user_id = current_user.get("sub")
    count = await notification_service.get_unread_count(user_id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    user_id = current_user.get("sub")
    
    success = await notification_service.mark_as_read(user_id, notification_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    user_id = current_user.get("sub")
    count = await notification_service.mark_all_as_read(user_id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification."""
    user_id = current_user.get("sub")
    
    success = await notification_service.delete_notification(user_id, notification_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification deleted"}


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a notification (admin only)."""
    # TODO: Add admin role check
    
    notification = Notification(
        user_id=request.user_id,
        title=request.title,
        message=request.message,
        notification_type=NotificationType(request.type),
        channels=[NotificationChannel(c) for c in request.channels],
        action_url=request.action_url,
        data=request.data or {}
    )
    
    success = await notification_service.send(notification)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )
    
    logger.info("notification_sent_via_api", user_id=request.user_id, title=request.title)
    
    return {"message": "Notification sent", "notification_id": notification.id}
