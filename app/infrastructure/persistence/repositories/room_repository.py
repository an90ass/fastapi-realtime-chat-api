"""
SqlAlchemyRoomRepository — concrete implementation of IRoomRepository.

Responsibilities:
  1. Execute async SQLAlchemy queries for rooms and memberships.
  2. Map ORM RoomModel / RoomMemberModel ↔ Domain entities.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.room import RoomEntity, RoomMemberEntity
from app.infrastructure.persistence.models.room_model import RoomMemberModel, RoomModel
from app.infrastructure.persistence.repositories.base import BaseSqlAlchemyRepository


def _room_to_entity(model: RoomModel) -> RoomEntity:
    return RoomEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        is_private=bool(model.is_private),
        created_at=model.created_at,
    )


def _member_to_entity(model: RoomMemberModel) -> RoomMemberEntity:
    return RoomMemberEntity(
        id=model.id,
        room_id=model.room_id,
        user_id=model.user_id,
        joined_at=model.joined_at,
    )


class SqlAlchemyRoomRepository(BaseSqlAlchemyRepository[RoomModel]):
    """Concrete async room repository. Implements IRoomRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RoomModel, db)

    async def get_by_id(self, room_id: int) -> Optional[RoomEntity]:
        model = await self._get_by_id(room_id)
        return _room_to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Optional[RoomEntity]:
        result = await self._db.execute(
            select(RoomModel).where(RoomModel.name == name)
        )
        model = result.scalars().first()
        return _room_to_entity(model) if model else None

    async def get_public_rooms(self, skip: int = 0, limit: int = 50) -> List[RoomEntity]:
        result = await self._db.execute(
            select(RoomModel)
            .where(RoomModel.is_private.is_(False))
            .offset(skip)
            .limit(limit)
        )
        return [_room_to_entity(m) for m in result.scalars().all()]

    async def create(self, entity: RoomEntity) -> RoomEntity:
        orm = RoomModel(
            name=entity.name,
            description=entity.description,
            is_private=entity.is_private,
        )
        saved = await self._persist(orm)
        return _room_to_entity(saved)

    async def is_member(self, room_id: int, user_id: int) -> bool:
        result = await self._db.execute(
            select(RoomMemberModel).where(
                RoomMemberModel.room_id == room_id,
                RoomMemberModel.user_id == user_id,
            )
        )
        return result.scalars().first() is not None

    async def add_member(self, room_id: int, user_id: int) -> RoomMemberEntity:
        orm = RoomMemberModel(room_id=room_id, user_id=user_id)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return _member_to_entity(orm)

    async def get_room_members(self, room_id: int) -> List[RoomMemberEntity]:
        result = await self._db.execute(
            select(RoomMemberModel).where(RoomMemberModel.room_id == room_id)
        )
        return [_member_to_entity(m) for m in result.scalars().all()]
