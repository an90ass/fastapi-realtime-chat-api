"""
ConnectionManager — maintains local WebSocket connections partitioned by room.

This is a presentation-layer concern: it tracks which sockets are connected
on THIS server instance. Across multiple server nodes, cross-instance delivery
is handled by the RedisPubSubManager.
"""

import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active local WebSocket connections, grouped by room_id."""

    def __init__(self) -> None:
        self._rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for a room."""
        await websocket.accept()
        self._rooms.setdefault(room_id, set()).add(websocket)
        logger.info(
            "WS connected: room=%s total_in_room=%s", room_id, len(self._rooms[room_id])
        )

    def disconnect(self, room_id: int, websocket: WebSocket) -> int:
        """Unregister a WebSocket. Returns remaining connection count for the room."""
        room = self._rooms.get(room_id)
        if room and websocket in room:
            room.discard(websocket)
            remaining = len(room)
            if remaining == 0:
                del self._rooms[room_id]
            logger.info("WS disconnected: room=%s remaining=%s", room_id, remaining)
            return remaining
        return 0

    def get_room_count(self, room_id: int) -> int:
        """Return the number of active local connections in the room."""
        return len(self._rooms.get(room_id, set()))

    async def broadcast_to_room(self, room_id: int, message: Any) -> None:
        """Broadcast a payload to all locally connected clients in a room."""
        room = self._rooms.get(room_id)
        if not room:
            return

        payload = (
            json.dumps(message) if isinstance(message, (dict, list)) else str(message)
        )
        dead: Set[WebSocket] = set()

        for ws in list(room):
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.warning("Dead socket in room=%s: %s", room_id, exc)
                dead.add(ws)

        for ws in dead:
            self.disconnect(room_id, ws)


connection_manager = ConnectionManager()
