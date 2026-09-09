"""
ChatService — Application Use Case for sending and retrieving chat messages.

Critical Clean Architecture fix applied here:
  ✅ IMessageBroker (domain port) replaces the direct `redis_client` import.
  ✅ IRoomRepository (domain port) replaces RoomService inter-service dependency.
  ✅ Zero knowledge of Redis, SQLAlchemy, FastAPI, or Pydantic.

Dependency graph (no violations):
  ChatService → IMessageRepository  (domain port)
  ChatService → IRoomRepository     (domain port)
  ChatService → IMessageBroker      (domain port)
  ChatService → core/exceptions
  ChatService → domain entities + application commands/results
"""

from typing import Optional

from app.application.commands import MessagePageResult
from app.core.exceptions import AuthorizationError
from app.domain.entities.message import MessageEntity
from app.domain.ports.message_broker import IMessageBroker
from app.domain.ports.repositories import IMessageRepository, IRoomRepository


class ChatService:
    """Use case orchestrating message persistence, retrieval, and broadcasting."""

    def __init__(
        self,
        message_repo: IMessageRepository,
        room_repo: IRoomRepository,
        broker: IMessageBroker,
    ) -> None:
        self._message_repo = message_repo
        self._room_repo = room_repo
        self._broker = broker

    async def get_messages(
        self,
        room_id: int,
        user_id: int,
        limit: int = 50,
        before_id: Optional[int] = None,
    ) -> MessagePageResult:
        """Return cursor-paginated message history after verifying membership."""
        if not await self._room_repo.is_member(room_id, user_id):
            raise AuthorizationError("You are not a member of this chat room.")

        messages, next_cursor, has_more = await self._message_repo.get_messages_cursor(
            room_id=room_id,
            limit=limit,
            before_id=before_id,
        )
        return MessagePageResult(
            items=tuple(messages),
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def send_message(
        self,
        content: str,
        room_id: int,
        sender_id: int,
        sender_username: str,
    ) -> MessageEntity:
        """
        Persist a message, set its sender metadata, and publish to the broker.
        The broker abstraction (IMessageBroker) ensures this use case has
        zero awareness of Redis — it could just as easily be Kafka or RabbitMQ.
        """
        if not await self._room_repo.is_member(room_id, sender_id):
            raise AuthorizationError("You are not a member of this chat room.")

        saved = await self._message_repo.save_message(
            content=content,
            room_id=room_id,
            sender_id=sender_id,
        )
        # Enrich entity with sender username (known by caller; avoids extra DB query)
        saved.sender_username = sender_username

        # Publish via abstract broker — no Redis knowledge here
        channel = f"room:{room_id}"
        await self._broker.publish(
            channel,
            {
                "id": saved.id,
                "content": saved.content,
                "room_id": room_id,
                "sender_id": sender_id,
                "username": sender_username,
                "created_at": str(saved.created_at),
            },
        )
        return saved
