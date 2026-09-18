"""
Notification Service — creates, delivers, and manages user notifications.

This is the single entry point for all notification creation. Call
`notification_service.create_notification(...)` from event handlers or
directly from services when a significant event occurs.

Real-time delivery:
  If the target user has an open WebSocket connection, the notification is
  pushed immediately. Otherwise it sits in the DB as unread until the user
  opens the app.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository


class NotificationService:
    def __init__(
        self,
        db: AsyncSession,
        ws_manager=None,
    ):
        self.db = db
        self.repo = NotificationRepository(db)
        # Lazy import to avoid circular deps at module load time
        self._ws_manager = ws_manager

    @property
    def ws_manager(self):
        if self._ws_manager is None:
            from app.api.websockets.notification_ws import notification_ws_manager
            self._ws_manager = notification_ws_manager
        return self._ws_manager

    async def create_notification(
        self,
        org_id: str,
        user_id: str,
        type: str,
        title: str,
        body: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        priority: str = "NORMAL",
        metadata: dict | None = None,
    ) -> Notification:
        """
        1. Persist notification to DB.
        2. Push via WebSocket if user is currently connected.
        3. Return the notification.
        """
        notif = await self.repo.create(
            organization_id=org_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            notification_metadata=metadata,
        )
        await self.db.commit()
        await self.db.refresh(notif)

        # Real-time push
        if self.ws_manager.is_connected(user_id):
            unread_count = await self.repo.get_unread_count(user_id)
            notif_dict = {
                "id": notif.id,
                "type": notif.type,
                "title": notif.title,
                "body": notif.body,
                "entity_type": notif.entity_type,
                "entity_id": notif.entity_id,
                "priority": notif.priority,
                "is_read": notif.is_read,
                "created_at": (
                    notif.created_at.isoformat()
                    if hasattr(notif.created_at, "isoformat")
                    else str(notif.created_at)
                ),
            }
            await self.ws_manager.push_notification(user_id, notif_dict)
            await self.ws_manager.push_unread_count(user_id, unread_count)

        return notif

    async def create_for_org_roles(
        self,
        org_id: str,
        role_names: list[str],
        type: str,
        title: str,
        body: str,
        **kwargs,
    ) -> list[Notification]:
        """Create and deliver a notification for all active users with specified roles in the org."""
        user_ids = await self.repo.get_users_by_org_roles(org_id, role_names)
        notifications = []
        for uid in user_ids:
            notif = await self.create_notification(
                org_id=org_id,
                user_id=uid,
                type=type,
                title=title,
                body=body,
                **kwargs,
            )
            notifications.append(notif)
        return notifications

    async def create_for_org_admins(
        self,
        org_id: str,
        type: str,
        title: str,
        body: str,
        **kwargs,
    ) -> list[Notification]:
        """Create notifications for OWNER and ADMIN users in the org."""
        return await self.create_for_org_roles(
            org_id, ["OWNER", "ADMIN"], type, title, body, **kwargs
        )

    async def mark_read(self, notification_id: str, user_id: str) -> None:
        await self.repo.mark_read(notification_id, user_id)
        await self.db.commit()

    async def mark_all_read(self, user_id: str) -> None:
        await self.repo.mark_all_read(user_id)
        await self.db.commit()
        # Push zeroed unread count
        if self.ws_manager.is_connected(user_id):
            await self.ws_manager.push_unread_count(user_id, 0)

    async def get_unread_count(self, user_id: str) -> int:
        return await self.repo.get_unread_count(user_id)

    async def list_notifications(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        return await self.repo.list_by_user(
            user_id, page=page, page_size=page_size, unread_only=unread_only
        )

    async def delete_notification(self, notification_id: str, user_id: str) -> None:
        await self.repo.delete(notification_id, user_id)
        await self.db.commit()
