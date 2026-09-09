"""
Repository Port Interfaces — define the abstract data-access contracts
that the Application layer depends on. Concrete implementations live
in app/infrastructure/persistence/repositories/.

By depending only on these Protocols (not on SQLAlchemy, Redis, or any
concrete class), the Application layer remains fully isolated from
infrastructure — the cornerstone of the Dependency Inversion Principle.
"""

from typing import List, Optional, Protocol, Tuple, runtime_checkable

from app.domain.entities.message import MessageEntity
from app.domain.entities.room import RoomEntity, RoomMemberEntity
from app.domain.entities.user import UserEntity


@runtime_checkable
class IUserRepository(Protocol):
    """Abstract contract for user persistence operations."""

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]: ...

    async def get_by_email(self, email: str) -> Optional[UserEntity]: ...

    async def get_by_username(self, username: str) -> Optional[UserEntity]: ...

    async def create(self, entity: UserEntity) -> UserEntity: ...


@runtime_checkable
class IRoomRepository(Protocol):
    """Abstract contract for room and membership persistence operations."""

    async def get_by_id(self, room_id: int) -> Optional[RoomEntity]: ...

    async def get_by_name(self, name: str) -> Optional[RoomEntity]: ...

    async def get_public_rooms(self, skip: int, limit: int) -> List[RoomEntity]: ...

    async def create(self, entity: RoomEntity) -> RoomEntity: ...

    async def is_member(self, room_id: int, user_id: int) -> bool: ...

    async def add_member(self, room_id: int, user_id: int) -> RoomMemberEntity: ...

    async def get_room_members(self, room_id: int) -> List[RoomMemberEntity]: ...


@runtime_checkable
class IMessageRepository(Protocol):
    """Abstract contract for message persistence and pagination operations."""

    async def save_message(
        self,
        content: str,
        room_id: int,
        sender_id: int,
    ) -> MessageEntity: ...

    async def get_messages_cursor(
        self,
        room_id: int,
        limit: int,
        before_id: Optional[int],
    ) -> Tuple[List[MessageEntity], Optional[int], bool]: ...
