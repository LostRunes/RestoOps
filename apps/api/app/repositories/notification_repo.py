from datetime import datetime, timezone
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **data) -> Notification:
        notif = Notification(**data)
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def get_by_id(self, notification_id: str, user_id: str) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            base = base.where(Notification.is_read == False)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        # Paginated items ordered newest first
        stmt = (
            base
            .order_by(Notification.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def mark_read(self, notification_id: str, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=now)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def mark_all_read(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=now)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_unread_count(self, user_id: str) -> int:
        stmt = select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, notification_id: str, user_id: str) -> None:
        notif = await self.get_by_id(notification_id, user_id)
        if notif:
            await self.db.delete(notif)
            await self.db.flush()

    async def get_users_by_org_roles(
        self,
        org_id: str,
        role_names: list[str],
    ) -> list[str]:
        """Return user_ids for all active users in the org with specified roles."""
        from sqlalchemy.orm import selectinload
        from app.models.user import User
        from app.models.role import Role

        stmt = (
            select(User.id)
            .join(Role, User.role_id == Role.id)
            .where(
                User.organization_id == org_id,
                User.is_active == True,
                Role.name.in_(role_names),
            )
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]
