"""
SqlAlchemyMessageRepository — concrete implementation of IMessageRepository.

Responsibilities:
  1. Cursor-based pagination with a composite index join for high performance.
  2. Eager username denormalization via a single JOIN (no N+1 queries).
  3. Map ORM rows → Domain MessageEntity (Anti-Corruption Layer).
"""

from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.message import MessageEntity
from app.infrastructure.persistence.models.message_model import MessageModel
from app.infrastructure.persistence.models.user_model import UserModel
from app.infrastructure.persistence.repositories.base import BaseSqlAlchemyRepository


class SqlAlchemyMessageRepository(BaseSqlAlchemyRepository[MessageModel]):
    """Concrete async message repository. Implements IMessageRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(MessageModel, db)

    async def save_message(
        self,
        content: str,
        room_id: int,
        sender_id: int,
    ) -> MessageEntity:
        """Persist a new message and return a domain entity (no sender_username yet)."""
        orm = MessageModel(content=content, room_id=room_id, sender_id=sender_id)
        saved = await self._persist(orm)
        return MessageEntity(
            id=saved.id,
            content=saved.content,
            room_id=saved.room_id,
            sender_id=saved.sender_id,
            sender_username=None,
            created_at=saved.created_at,
        )

    async def get_messages_cursor(
        self,
        room_id: int,
        limit: int,
        before_id: Optional[int],
    ) -> Tuple[List[MessageEntity], Optional[int], bool]:
        """
        High-performance cursor pagination using the composite index (room_id, id).
        Fetches sender username via single JOIN — zero N+1 queries.
        Returns: (page_entities, next_cursor, has_more)
        """
        query = (
            select(MessageModel, UserModel.username)
            .join(UserModel, MessageModel.sender_id == UserModel.id)
            .where(MessageModel.room_id == room_id)
        )
        if before_id is not None:
            query = query.where(MessageModel.id < before_id)

        # Fetch limit + 1 to detect whether there are more pages
        query = query.order_by(MessageModel.id.desc()).limit(limit + 1)
        result = await self._db.execute(query)
        rows = result.all()

        has_more = len(rows) > limit
        page_rows = rows[:limit] if has_more else rows
        next_cursor = page_rows[-1][0].id if (has_more and page_rows) else None

        # Reverse to return chronological order for chat history display
        page_rows.reverse()

        entities = [
            MessageEntity(
                id=row[0].id,
                content=row[0].content,
                room_id=row[0].room_id,
                sender_id=row[0].sender_id,
                sender_username=row[1],
                created_at=row[0].created_at,
            )
            for row in page_rows
        ]
        return entities, next_cursor, has_more
