from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.lead_activity import LeadActivity
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.schemas.conversation import ConversationDetailResponse, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.email_service import EmailService

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    status: str | None = None,
    lead_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    repo = ConversationRepository(db)
    filters = {"status": status, "lead_id": lead_id}
    convs = await repo.list_by_org(current_user.organization_id, filters=filters)
    res = []
    for c in convs:
        item = ConversationResponse.model_validate(c)
        if c.lead:
            item.lead_email = c.lead.email
            item.lead_contact_name = c.lead.contact_name
        res.append(item)
    return res


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    repo = ConversationRepository(db)
    conv = await repo.get_by_id(conversation_id, current_user.organization_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    res = ConversationDetailResponse.model_validate(conv)
    if conv.lead:
        res.lead_email = conv.lead.email
        res.lead_contact_name = conv.lead.contact_name
    return res


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conversation_id, current_user.organization_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_repo = MessageRepository(db)
    return await msg_repo.list_by_conversation(conversation_id)


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_manual_reply(
    conversation_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conversation_id, current_user.organization_id)
    if not conv or not conv.lead:
        raise HTTPException(status_code=404, detail="Conversation or lead not found")

    email_service = EmailService()
    sender_email = getattr(email_service.provider, "default_from_addr", "noreply@restoops.local")
    subject = payload.subject or conv.subject or "Re: Outreach"

    # Send outbound email via EmailService
    send_res = await email_service.send_email(
        to=conv.lead.email or "",
        subject=subject,
        body_html=f"<div>{payload.body}</div>",
        body_text=payload.body,
        from_addr=sender_email,
    )

    if not send_res.success:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {send_res.error}")

    msg_repo = MessageRepository(db)
    msg = await msg_repo.create(
        conversation_id=conv.id,
        direction="OUTBOUND",
        sender=sender_email,
        recipient=conv.lead.email or "",
        subject=subject,
        body=payload.body,
        message_id=send_res.message_id,
        status="SENT",
    )

    # Log activity
    activity = LeadActivity(
        lead_id=conv.lead_id,
        activity_type="EMAIL_SENT",
        description=f"Manual email sent: {subject}",
        activity_metadata={"message_id": msg.id, "sender": sender_email},
    )
    db.add(activity)
    await db.commit()

    return msg
