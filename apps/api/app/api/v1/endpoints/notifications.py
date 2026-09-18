from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """List notifications for the current user, newest first."""
    svc = NotificationService(db)
    notifications, total = await svc.list_notifications(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    unread_count = await svc.get_unread_count(current_user.id)
    return NotificationListResponse(
        notifications=notifications,
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.get("/count", response_model=UnreadCountResponse)
@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Fast unread notification count for badge display."""
    svc = NotificationService(db)
    count = await svc.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Mark all unread notifications as read and push updated count via WebSocket."""
    svc = NotificationService(db)
    await svc.mark_all_read(current_user.id)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Mark a single notification as read."""
    svc = NotificationService(db)
    await svc.mark_read(notification_id, current_user.id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a notification. Only the notification's owner can delete it."""
    svc = NotificationService(db)
    await svc.delete_notification(notification_id, current_user.id)
