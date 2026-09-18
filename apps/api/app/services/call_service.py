from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import Event, EventBus, EventType
from app.integrations.call_base import CallRequest
from app.integrations.exotel.provider import ExotelProvider, EXOTEL_STATUS_MAP
from app.integrations.webrtc.provider import WebRTCProvider
from app.models.call import Call
from app.models.lead_activity import LeadActivity
from app.repositories.call_repo import CallRepository

# Terminal statuses from Exotel — call is definitely over
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "BUSY", "NO_ANSWER", "CANCELLED"}

# Stun servers for frontend WebRTC configuration
STUN_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
]


class CallService:
    """
    Facade that coordinates call lifecycle across Exotel and WebRTC providers.

    Responsibilities:
    - start_call(): validate input, call provider, persist call record, log activity
    - end_call(): mark call cancelled, log activity
    - handle_exotel_status(): process incoming Exotel status webhooks
    - get_call() / list_calls(): read operations
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CallRepository(db)
        self.exotel = ExotelProvider()
        self.webrtc = WebRTCProvider()

    def _select_provider(self, provider_type: str):
        if provider_type.upper() == "EXOTEL":
            return self.exotel
        elif provider_type.upper() == "WEBRTC":
            return self.webrtc
        raise ValueError(f"Unknown provider: {provider_type}. Use EXOTEL or WEBRTC")

    async def start_call(
        self,
        org_id: str,
        lead_id: str,
        provider_type: str,
        from_identifier: str,
        to_identifier: str,
        initiated_by: str,
        restaurant_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Call:
        """
        Initiate a call:
        1. Select provider (EXOTEL or WEBRTC)
        2. Create INITIATED call record in DB
        3. Call provider.initiate_call()
        4. Update call record with provider call ID and status
        5. Log lead activity
        6. Return call record
        """
        from uuid import UUID
        provider = self._select_provider(provider_type)

        # Create call record in DB before calling provider so we always have a record
        call = await self.repo.create(
            organization_id=org_id,
            lead_id=lead_id,
            restaurant_id=restaurant_id,
            conversation_id=conversation_id,
            provider=provider_type.upper(),
            direction="OUTBOUND",
            from_number=from_identifier,
            to_number=to_identifier,
            status="INITIATED",
            initiated_by=initiated_by,
            started_at=datetime.now(timezone.utc),
        )

        # Log INITIATED event
        await self.repo.add_event(call.id, "INITIATED", source="SYSTEM")

        # Call the provider
        result = await provider.initiate_call(
            CallRequest(
                lead_id=UUID(lead_id),
                from_identifier=from_identifier,
                to_identifier=to_identifier,
                org_id=UUID(org_id),
                initiated_by=UUID(initiated_by),
            )
        )

        # Update call with provider result
        update_data: dict = {"status": result.status}
        if result.call_id:
            update_data["exotel_call_sid"] = result.call_id
        if not result.success:
            update_data["status"] = "FAILED"
            update_data["ended_at"] = datetime.now(timezone.utc)

        call = await self.repo.update(call.id, **update_data)

        # Log provider result event
        if result.success:
            await self.repo.add_event(
                call.id, "PROVIDER_INITIATED",
                payload={"provider_call_id": result.call_id, "status": result.status},
                source="SYSTEM",
            )
        else:
            await self.repo.add_event(
                call.id, "FAILED",
                payload={"error": result.error},
                source="SYSTEM",
            )

        # Log lead activity
        activity = LeadActivity(
            lead_id=lead_id,
            user_id=initiated_by,
            activity_type="CALL_STARTED",
            description=f"{provider_type.upper()} call initiated to {to_identifier}",
            activity_metadata={
                "call_id": call.id,
                "provider": provider_type.upper(),
                "success": result.success,
                "error": result.error,
            },
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(call)

        await EventBus.publish(Event(
            EventType.CALL_STARTED, org_id,
            {"call_id": call.id, "lead_id": lead_id,
             "provider": provider_type.upper(), "to": to_identifier},
            user_id=initiated_by,
        ))
        return call

    async def end_call(self, call_id: str, org_id: str) -> Call:
        """
        Cancel/end an active call.
        Note: Exotel does not support a hangup API in v1 trial —
        we mark it CANCELLED in our DB. Exotel will deliver a terminal webhook naturally.
        """
        call = await self.repo.get_by_id(call_id, org_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")
        if call.status in TERMINAL_STATUSES:
            raise ValueError(f"Call is already in terminal status: {call.status}")

        provider = self._select_provider(call.provider)
        provider_call_id = call.exotel_call_sid or call_id
        await provider.end_call(provider_call_id)

        call = await self.repo.update(
            call_id,
            status="CANCELLED",
            ended_at=datetime.now(timezone.utc),
        )
        await self.repo.add_event(call_id, "ENDED", payload={"reason": "MANUAL_CANCEL"})
        await self.db.commit()
        await self.db.refresh(call)
        return call

    async def handle_exotel_status(
        self,
        call_sid: str,
        raw_status: str,
        duration: int | None = None,
        recording_url: str | None = None,
    ) -> None:
        """
        Process an Exotel StatusCallback webhook.
        Maps Exotel status → our status, updates call record and events.
        """
        our_status = EXOTEL_STATUS_MAP.get(raw_status.lower(), "UNKNOWN")
        call = await self.repo.get_by_exotel_sid(call_sid)
        if not call:
            return  # Unknown SID — possibly from a different system

        update_data: dict = {"status": our_status}

        if our_status == "IN_PROGRESS" and not call.answered_at:
            update_data["answered_at"] = datetime.now(timezone.utc)

        if our_status in TERMINAL_STATUSES:
            update_data["ended_at"] = datetime.now(timezone.utc)
            if duration is not None:
                update_data["duration_seconds"] = duration
            if recording_url:
                update_data["recording_url"] = recording_url

        await self.repo.update(call.id, **update_data)

        event_type = "ENDED" if our_status in TERMINAL_STATUSES else "STATUS_UPDATE"
        await self.repo.add_event(
            call.id,
            event_type,
            payload={
                "exotel_status": raw_status,
                "our_status": our_status,
                "duration": duration,
                "recording_url": recording_url,
            },
            source="EXOTEL_WEBHOOK",
        )

        if our_status in TERMINAL_STATUSES:
            # Log lead activity
            activity = LeadActivity(
                lead_id=call.lead_id,
                user_id=call.initiated_by,
                activity_type="CALL_COMPLETED",
                description=f"Call ended with status {our_status}"
                + (f", duration {duration}s" if duration else ""),
                activity_metadata={
                    "call_id": call.id,
                    "status": our_status,
                    "duration_seconds": duration,
                    "recording_url": recording_url,
                },
            )
            self.db.add(activity)

        await self.db.commit()

        if our_status in TERMINAL_STATUSES:
            await EventBus.publish(Event(
                EventType.CALL_ENDED, call.organization_id,
                {"call_id": call.id, "lead_id": call.lead_id,
                 "status": our_status, "duration_seconds": duration,
                 "recording_url": recording_url},
                user_id=call.initiated_by,
            ))

    async def get_call(self, call_id: str, org_id: str) -> Call:
        call = await self.repo.get_by_id(call_id, org_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")
        return call

    async def list_calls(
        self,
        org_id: str,
        lead_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Call]:
        return await self.repo.list_by_org(org_id, lead_id=lead_id, limit=limit, offset=offset)

    async def get_events(self, call_id: str, org_id: str) -> list:
        call = await self.repo.get_by_id(call_id, org_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")
        return await self.repo.get_events(call_id)

    @staticmethod
    def get_stun_servers() -> list[dict]:
        """Return STUN server config for frontend WebRTC ICE configuration."""
        return STUN_SERVERS
