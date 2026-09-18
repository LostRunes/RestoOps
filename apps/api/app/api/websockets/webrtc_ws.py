"""
WebRTC Signaling Server via WebSockets.

Flow:
  1. Frontend calls POST /api/v1/calls with provider=WEBRTC → gets back a call record
     where exotel_call_sid is the room_id.
  2. Both participants connect: ws://.../ws/webrtc/{room_id}?token={jwt}
  3. This server relays SDP offer/answer and ICE candidates between them.
  4. When either disconnects, peers are notified.

Message protocol (JSON):
{
  "type": "offer" | "answer" | "ice-candidate" | "hangup" | "joined",
  "payload": { ... },   // SDP or ICE candidate data
  "from": "user_id"     // populated by server on relay
}
"""
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


class WebRTCSignalingManager:
    """
    In-memory WebSocket connection registry per room.
    Structure: rooms[room_id][user_id] = websocket

    NOTE: This is in-memory — works for single-instance dev deployments.
    For multi-process / multi-server prod, use Redis pub/sub here instead.
    """

    def __init__(self):
        self.rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str) -> None:
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][user_id] = websocket
        logger.info(f"WebRTC: {user_id} joined room {room_id}")

        # Notify other participants in the room that a new peer joined
        await self._broadcast_except(
            room_id,
            sender_id=user_id,
            message={"type": "peer-joined", "from": user_id},
        )

    async def disconnect(self, room_id: str, user_id: str) -> None:
        if room_id in self.rooms:
            self.rooms[room_id].pop(user_id, None)
            logger.info(f"WebRTC: {user_id} left room {room_id}")

            # Notify remaining participants
            await self._broadcast_except(
                room_id,
                sender_id=user_id,
                message={"type": "peer-left", "from": user_id},
            )

            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                logger.info(f"WebRTC: room {room_id} closed (empty)")

    async def relay_message(self, room_id: str, sender_id: str, message: dict) -> None:
        """
        Relay a signaling message from sender to all other participants in the room.
        Attaches the sender's user_id as `from` field.
        """
        message["from"] = sender_id
        await self._broadcast_except(room_id, sender_id=sender_id, message=message)

    async def send_to(self, room_id: str, user_id: str, message: dict) -> None:
        """Send a message to a specific user in a room."""
        ws = self.rooms.get(room_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

    async def _broadcast_except(
        self, room_id: str, sender_id: str, message: dict
    ) -> None:
        """Send message to all peers in the room except the sender."""
        if room_id not in self.rooms:
            return
        payload = json.dumps(message)
        for uid, ws in list(self.rooms[room_id].items()):
            if uid == sender_id:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                logger.warning(f"WebRTC: failed to send to {uid} in room {room_id}")


# Module-level singleton — shared across all WebSocket connections
signaling_manager = WebRTCSignalingManager()


async def _authenticate_ws(token: str | None) -> str | None:
    """Decode JWT from query param and return user_id, or None if invalid."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except Exception:
        return None


@router.websocket("/ws/webrtc/{room_id}")
async def webrtc_signaling(
    websocket: WebSocket,
    room_id: str,
    token: str | None = Query(default=None),
):
    """
    WebRTC signaling WebSocket endpoint.

    Connect as: ws://localhost:8000/ws/webrtc/{room_id}?token={jwt_access_token}

    Supported message types (send from client):
    - offer      { type, payload: { sdp } }
    - answer     { type, payload: { sdp } }
    - ice-candidate { type, payload: { candidate, sdpMid, sdpMLineIndex } }
    - hangup     { type }

    Messages received from server:
    - peer-joined   { type, from: user_id }
    - peer-left     { type, from: user_id }
    - offer / answer / ice-candidate / hangup (relayed from peer, with `from`)
    """
    user_id = await _authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await signaling_manager.connect(websocket, room_id, user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type", "")
            if msg_type == "hangup":
                # Relay hangup then close
                await signaling_manager.relay_message(room_id, user_id, message)
                break
            else:
                await signaling_manager.relay_message(room_id, user_id, message)

    except WebSocketDisconnect:
        pass
    finally:
        await signaling_manager.disconnect(room_id, user_id)
