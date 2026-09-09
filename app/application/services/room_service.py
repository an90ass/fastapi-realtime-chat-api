"""
RoomService — Application Use Case for room management and membership control.

Dependency graph (no violations):
  RoomService → IRoomRepository (domain port)
  RoomService → core/exceptions
  RoomService → domain entities + application commands

Zero imports from: SQLAlchemy, FastAPI, Redis, or any Pydantic schema.
"""

from typing import List

from app.application.commands import CreateRoomCommand
from app.core.exceptions import (
    AuthorizationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
)
from app.domain.entities.room import RoomEntity, RoomMemberEntity
from app.domain.ports.repositories import IRoomRepository


class RoomService:
    """Use case managing room lifecycle and membership rules."""

    def __init__(self, room_repo: IRoomRepository) -> None:
        self._room_repo = room_repo

    async def create_room(self, cmd: CreateRoomCommand) -> RoomEntity:
        """Create a new room and automatically enlist the creator as its first member."""
        if await self._room_repo.get_by_name(cmd.name):
            raise EntityAlreadyExistsError(f"Room '{cmd.name}' already exists.")

        new_room = RoomEntity(
            name=cmd.name,
            description=cmd.description,
            is_private=cmd.is_private,
        )
        created = await self._room_repo.create(new_room)
        await self._room_repo.add_member(created.id, cmd.creator_id)
        return created

    async def list_public_rooms(self, skip: int = 0, limit: int = 50) -> List[RoomEntity]:
        """Return all public rooms with offset pagination."""
        return await self._room_repo.get_public_rooms(skip=skip, limit=limit)

    async def get_room(self, room_id: int) -> RoomEntity:
        """Fetch a room or raise EntityNotFoundError."""
        room = await self._room_repo.get_by_id(room_id)
        if not room:
            raise EntityNotFoundError("Room", room_id)
        return room

    async def join_room(self, room_id: int, user_id: int) -> RoomMemberEntity:
        """Enlist a user into a room after validating existence and uniqueness."""
        await self.get_room(room_id)
        if await self._room_repo.is_member(room_id, user_id):
            raise EntityAlreadyExistsError("User is already a member of this room.")
        return await self._room_repo.add_member(room_id, user_id)

    async def get_room_members(self, room_id: int) -> List[RoomMemberEntity]:
        """Return all membership records for a room."""
        await self.get_room(room_id)
        return await self._room_repo.get_room_members(room_id)

    async def check_membership(self, room_id: int, user_id: int) -> None:
        """Raise AuthorizationError if the user is not a room member."""
        if not await self._room_repo.is_member(room_id, user_id):
            raise AuthorizationError("You are not a member of this chat room.")
