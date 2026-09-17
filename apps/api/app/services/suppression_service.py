from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suppression import SuppressionEntry


class SuppressionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_suppressed(self, org_id: str, email: str | None = None, phone: str | None = None) -> bool:
        if not email and not phone:
            return False

        stmt = select(SuppressionEntry).where(SuppressionEntry.organization_id == org_id)
        if email:
            stmt = stmt.where(SuppressionEntry.email == email.strip().lower())
        elif phone:
            stmt = stmt.where(SuppressionEntry.phone == phone.strip())

        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
