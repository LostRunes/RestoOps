import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.core.config import settings


class WebRTCRoomManager:
    """
    Manages WebRTC call room state in Redis.

    Room key: webrtc:room:{room_id}
    Value: JSON dict with caller_id, callee_id, status, created_at, joined
    TTL: 3600 seconds (1 hour)
    """

    TTL = 3600
    KEY_PREFIX = "webrtc:room:"

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _key(self, room_id: str) -> str:
        return f"{self.KEY_PREFIX}{room_id}"

    async def create_room(self, caller_id: str, callee_id: str) -> dict:
        """Create a new room, store in Redis, return room dict with room_id."""
        room_id = str(uuid.uuid4())
        room = {
            "room_id": room_id,
            "caller_id": caller_id,
            "callee_id": callee_id,
            "status": "WAITING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "joined": [],
        }
        r = self._get_redis()
        await r.set(self._key(room_id), json.dumps(room), ex=self.TTL)
        return room

    async def join_room(self, room_id: str, user_id: str) -> dict | None:
        """Mark a participant as joined. Returns updated room or None if not found."""
        r = self._get_redis()
        raw = await r.get(self._key(room_id))
        if not raw:
            return None
        room = json.loads(raw)
        if user_id not in room["joined"]:
            room["joined"].append(user_id)
        if len(room["joined"]) >= 2:
            room["status"] = "ACTIVE"
        await r.set(self._key(room_id), json.dumps(room), ex=self.TTL)
        return room

    async def get_room(self, room_id: str) -> dict | None:
        """Fetch room state. Returns None if not found / expired."""
        r = self._get_redis()
        raw = await r.get(self._key(room_id))
        return json.loads(raw) if raw else None

    async def close_room(self, room_id: str) -> None:
        """Remove room from Redis."""
        r = self._get_redis()
        await r.delete(self._key(room_id))

    async def mark_ended(self, room_id: str) -> None:
        """Mark room as ENDED without deleting (preserves brief audit window)."""
        r = self._get_redis()
        raw = await r.get(self._key(room_id))
        if raw:
            room = json.loads(raw)
            room["status"] = "ENDED"
            await r.set(self._key(room_id), json.dumps(room), ex=300)  # 5 min audit TTL
