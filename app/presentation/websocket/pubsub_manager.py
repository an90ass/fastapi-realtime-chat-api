"""
RedisPubSubManager — coordinates Redis subscriptions with local WebSocket connections.

Single-Subscriber Multiplexing pattern:
  - At most ONE background task subscribes to each room's Redis channel per node.
  - All locally connected clients in that room receive messages from that single task.
  - When the last local client disconnects, the task is cancelled (no resource leaks).

This prevents the N² message duplication bug where N listeners each broadcast
to N clients, producing N² deliveries per published message.
"""

import asyncio
import json
import logging
from typing import Dict

from app.core.redis import redis_client
from app.presentation.websocket.connection_manager import ConnectionManager, connection_manager

logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """Manages one Redis subscription task per active room on this server node."""

    def __init__(self, conn_manager: ConnectionManager = connection_manager) -> None:
        self._conn_manager = conn_manager
        self._tasks: Dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def add_listener_if_needed(self, room_id: int) -> None:
        """Start the room's background Redis listener if not already running."""
        async with self._lock:
            existing = self._tasks.get(room_id)
            if existing is None or existing.done():
                task = asyncio.create_task(
                    self._listen(room_id), name=f"pubsub:room:{room_id}"
                )
                self._tasks[room_id] = task
                logger.info("Started PubSub listener: room=%s", room_id)

    async def remove_listener_if_empty(self, room_id: int) -> None:
        """Cancel the room's listener if there are no local clients left."""
        async with self._lock:
            if self._conn_manager.get_room_count(room_id) == 0:
                task = self._tasks.pop(room_id, None)
                if task and not task.done():
                    task.cancel()
                    logger.info("Cancelled PubSub listener: room=%s", room_id)

    async def _listen(self, room_id: int) -> None:
        """Background task: listen on room:{room_id} and dispatch to local sockets."""
        channel = f"room:{room_id}"
        pubsub = redis_client.get_pubsub()
        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    try:
                        raw = message["data"]
                        payload = json.loads(raw) if isinstance(raw, str) else raw
                        await self._conn_manager.broadcast_to_room(room_id, payload)
                    except Exception as exc:
                        logger.error("Error dispatching message room=%s: %s", room_id, exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("PubSub listener crashed room=%s: %s", room_id, exc)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    async def shutdown(self) -> None:
        """Gracefully cancel all running listener tasks on application shutdown."""
        async with self._lock:
            for task in self._tasks.values():
                if not task.done():
                    task.cancel()
            self._tasks.clear()
            logger.info("All PubSub listener tasks shut down.")


pubsub_manager = RedisPubSubManager()
