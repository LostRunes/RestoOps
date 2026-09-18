from app.integrations.call_base import CallProvider, CallRequest, CallResult
from app.integrations.webrtc.room_manager import WebRTCRoomManager


class WebRTCProvider(CallProvider):
    """
    WebRTC browser-to-browser call provider.

    Unlike Exotel, WebRTC does not make external API calls.
    The backend manages room state (Redis) and the browsers establish
    peer connections directly via WebSocket signaling.

    Flow:
      1. initiate_call() → creates a room in Redis → returns room_id as call_id
      2. Both participants connect to WS endpoint /ws/webrtc/{room_id}
      3. Signaling manager relays offer/answer/ICE between them
      4. end_call() → closes the room in Redis and notifies connected peers
    """

    def __init__(self):
        self.room_manager = WebRTCRoomManager()

    async def initiate_call(self, request: CallRequest) -> CallResult:
        """Create a WebRTC room for the two participants."""
        room = await self.room_manager.create_room(
            caller_id=str(request.from_identifier),
            callee_id=str(request.to_identifier),
        )
        return CallResult(
            success=True,
            call_id=room["room_id"],
            status="INITIATED",
            extra=room,
        )

    async def end_call(self, provider_call_id: str) -> bool:
        """Mark room as ended. WebSocket handler will notify connected peers."""
        await self.room_manager.mark_ended(provider_call_id)
        return True

    async def get_call_status(self, provider_call_id: str) -> str:
        """Check room status from Redis."""
        room = await self.room_manager.get_room(provider_call_id)
        if not room:
            return "COMPLETED"
        status_map = {
            "WAITING": "INITIATED",
            "ACTIVE": "IN_PROGRESS",
            "ENDED": "COMPLETED",
        }
        return status_map.get(room.get("status", ""), "UNKNOWN")
