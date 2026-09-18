"""
Real-time WebSocket notification delivery.

Each authenticated user can open a persistent WebSocket connection to
/ws/notifications?token=<jwt>. The server will:

1. Accept the connection and register it per user_id.
2. Immediately send an unread_count message.
3. Push any new notifications the moment they are created (from NotificationService).
4. Handle client-sent messages: ping/pong, mark_read.
5. Support multiple tabs/windows per user (list of connections per user_id).

Message formats (server → client):
  {"type": "unread_count", "data": {"count": 7}}
  {"type": "notification",  "data": {<NotificationResponse dict>}}
  {"type": "job_progress",  "data": {"job_id": "...", "processed": 100, "total": 500, "status": "RUNNING"}}
  {"type": "pong"}

Message formats (client → server):
  {"type": "ping"}
  {"type": "mark_read", "id": "<notification_id>"}
"""

import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationWSManager:
    """
    In-memory WebSocket registry keyed by user_id.
    One user can have multiple open connections (multiple browser tabs).
    """

    def __init__(self):
        # user_id → list of connected WebSockets
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
        logger.info(f"NotifWS: {user_id} connected ({len(self.connections[user_id])} tabs)")

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self.connections:
            try:
                self.connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.connections[user_id]:
                del self.connections[user_id]
                logger.info(f"NotifWS: {user_id} fully disconnected")

    def is_connected(self, user_id: str) -> bool:
        return bool(self.connections.get(user_id))

    async def push_notification(self, user_id: str, notification_data: dict) -> None:
        """Push a notification dict to all of this user's open connections."""
        await self._send_to_user(user_id, {"type": "notification", "data": notification_data})

    async def push_job_progress(self, user_id: str, job_id: str, progress: dict) -> None:
        """Push a job progress update to all of this user's open connections."""
        await self._send_to_user(
            user_id,
            {"type": "job_progress", "data": {"job_id": job_id, **progress}},
        )

    async def push_unread_count(self, user_id: str, count: int) -> None:
        """Push an updated unread count (e.g. after a new notification is created)."""
        await self._send_to_user(user_id, {"type": "unread_count", "data": {"count": count}})

    async def _send_to_user(self, user_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        # Clean up broken connections
        for ws in dead:
            await self.disconnect(ws, user_id)


# Module-level singleton shared across all WebSocket connections and services
notification_ws_manager = NotificationWSManager()


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


@router.websocket("/ws/notifications")
async def notification_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    """
    Notification WebSocket endpoint.

    Connect as: ws://localhost:8000/ws/notifications?token=<jwt_access_token>

    After connecting you'll immediately receive:
      {"type": "unread_count", "data": {"count": N}}

    Then whenever a notification is created for your user:
      {"type": "notification", "data": { ...NotificationResponse... }}

    You can send:
      {"type": "ping"}                    → server responds with {"type": "pong"}
      {"type": "mark_read", "id": "..."}  → marks notification as read (DB + unread count push)
    """
    from app.db.session import AsyncSessionLocal
    from app.repositories.notification_repo import NotificationRepository

    user_id = await _authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await notification_ws_manager.connect(websocket, user_id)

    # Send initial unread count
    async with AsyncSessionLocal() as db:
        repo = NotificationRepository(db)
        count = await repo.get_unread_count(user_id)
    await websocket.send_text(json.dumps({"type": "unread_count", "data": {"count": count}}))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "mark_read":
                notif_id = msg.get("id")
                if notif_id:
                    async with AsyncSessionLocal() as db:
                        repo = NotificationRepository(db)
                        await repo.mark_read(notif_id, user_id)
                        await db.commit()
                        count = await repo.get_unread_count(user_id)
                    # Push updated unread count to all tabs
                    await notification_ws_manager.push_unread_count(user_id, count)

    except WebSocketDisconnect:
        pass
    finally:
        await notification_ws_manager.disconnect(websocket, user_id)
