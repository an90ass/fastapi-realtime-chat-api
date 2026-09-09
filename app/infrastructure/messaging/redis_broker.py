"""
RedisMessageBroker — concrete implementation of IMessageBroker.

This class is the ONLY place in the entire codebase that knows Redis
is used for messaging. The Application layer (ChatService) calls
IMessageBroker.publish() — it never sees this class directly.

Implements: app.domain.ports.message_broker.IMessageBroker (structurally via Protocol).
"""

import json
from typing import Any

from app.core.redis import redis_client


class RedisMessageBroker:
    """Redis Pub/Sub backed implementation of IMessageBroker."""

    async def publish(self, channel: str, message: Any) -> None:
        """Serialize and publish a message to the given Redis channel."""
        payload = (
            json.dumps(message) if isinstance(message, (dict, list)) else str(message)
        )
        await redis_client.get_client().publish(channel, payload)
