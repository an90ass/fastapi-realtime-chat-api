"""
Message Broker Port Interface — abstract contract that decouples the
Application layer from any concrete messaging infrastructure (Redis, Kafka, etc.).

The Application layer calls IMessageBroker.publish() without knowing or caring
whether the underlying implementation uses Redis Pub/Sub, Kafka, RabbitMQ, or
an in-process queue — fulfilling the Dependency Inversion Principle.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IMessageBroker(Protocol):
    """Abstract contract for publishing messages to named channels."""

    async def publish(self, channel: str, message: Any) -> None: ...
