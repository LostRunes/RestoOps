from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        conversation_id: str,
        direction: str,
        sender: str,
        recipient: str,
        body: str,
        subject: str | None = None,
        message_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
        status: str = "SENT",
        activity_metadata: dict | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            direction=direction,
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            message_id=message_id,
            in_reply_to=in_reply_to,
            references=references,
            status=status,
            activity_metadata=activity_metadata,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def list_by_conversation(self, conversation_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_message_id(self, message_id_header: str) -> Message | None:
        if not message_id_header:
            return None
        stmt = select(Message).where(Message.message_id == message_id_header)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_references(self, references: list[str]) -> Message | None:
        if not references:
            return None
        stmt = (
            select(Message)
            .where(Message.message_id.in_(references))
            .order_by(Message.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
