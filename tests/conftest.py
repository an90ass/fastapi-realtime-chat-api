from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import pytest
    fixture = pytest.fixture
except ImportError:
    def fixture(*args, **kwargs):
        def decorator(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return decorator

from fastapi.testclient import TestClient

from app.application.services.auth_service import AuthService
from app.application.services.chat_service import ChatService
from app.application.services.room_service import RoomService
from app.core.security import create_access_token, hash_password
from app.domain.entities.message import MessageEntity
from app.domain.entities.room import RoomEntity, RoomMemberEntity
from app.domain.entities.user import UserEntity
from app.domain.ports.message_broker import IMessageBroker
from app.domain.ports.repositories import IMessageRepository, IRoomRepository, IUserRepository
from app.main import app
from app.presentation.dependencies import (
    get_auth_service,
    get_chat_service,
    get_message_broker,
    get_message_repository,
    get_room_repository,
    get_room_service,
    get_user_repository,
)


# ──────────────────────────────────────────────
# In-Memory Fakes (Implementing Domain Protocols)
# ──────────────────────────────────────────────

class FakeUserRepository:
    """In-memory implementation of IUserRepository."""

    def __init__(self) -> None:
        self.users: Dict[int, UserEntity] = {}
        self._current_id = 1

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def get_by_username(self, username: str) -> Optional[UserEntity]:
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    async def create(self, entity: UserEntity) -> UserEntity:
        user_id = self._current_id
        self._current_id += 1
        created = UserEntity(
            id=user_id,
            username=entity.username,
            email=entity.email,
            hashed_password=entity.hashed_password,
            is_active=entity.is_active,
            created_at=datetime.now(timezone.utc),
        )
        self.users[user_id] = created
        return created


class FakeRoomRepository:
    """In-memory implementation of IRoomRepository."""

    def __init__(self) -> None:
        self.rooms: Dict[int, RoomEntity] = {}
        self.members: List[RoomMemberEntity] = []
        self._room_id = 1
        self._member_id = 1

    async def get_by_id(self, room_id: int) -> Optional[RoomEntity]:
        return self.rooms.get(room_id)

    async def get_by_name(self, name: str) -> Optional[RoomEntity]:
        for r in self.rooms.values():
            if r.name == name:
                return r
        return None

    async def get_public_rooms(self, skip: int = 0, limit: int = 50) -> List[RoomEntity]:
        public = [r for r in self.rooms.values() if not r.is_private]
        return public[skip : skip + limit]

    async def create(self, entity: RoomEntity) -> RoomEntity:
        room_id = self._room_id
        self._room_id += 1
        created = RoomEntity(
            id=room_id,
            name=entity.name,
            description=entity.description,
            is_private=entity.is_private,
            created_at=datetime.now(timezone.utc),
        )
        self.rooms[room_id] = created
        return created

    async def is_member(self, room_id: int, user_id: int) -> bool:
        return any(m.room_id == room_id and m.user_id == user_id for m in self.members)

    async def add_member(self, room_id: int, user_id: int) -> RoomMemberEntity:
        member_id = self._member_id
        self._member_id += 1
        created = RoomMemberEntity(
            id=member_id,
            room_id=room_id,
            user_id=user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self.members.append(created)
        return created

    async def get_room_members(self, room_id: int) -> List[RoomMemberEntity]:
        return [m for m in self.members if m.room_id == room_id]


class FakeMessageRepository:
    """In-memory implementation of IMessageRepository with cursor pagination."""

    def __init__(self) -> None:
        self.messages: List[MessageEntity] = []
        self._msg_id = 1

    async def save_message(self, content: str, room_id: int, sender_id: int) -> MessageEntity:
        msg_id = self._msg_id
        self._msg_id += 1
        created = MessageEntity(
            id=msg_id,
            content=content,
            room_id=room_id,
            sender_id=sender_id,
            sender_username=None,
            created_at=datetime.now(timezone.utc),
        )
        self.messages.append(created)
        return created

    async def get_messages_cursor(
        self, room_id: int, limit: int = 50, before_id: Optional[int] = None
    ) -> Tuple[List[MessageEntity], Optional[int], bool]:
        room_msgs = [m for m in self.messages if m.room_id == room_id]
        if before_id is not None:
            room_msgs = [m for m in room_msgs if m.id < before_id]

        room_msgs.sort(key=lambda m: m.id, reverse=True)
        has_more = len(room_msgs) > limit
        page = room_msgs[:limit]
        next_cursor = page[-1].id if (has_more and page) else None

        page.reverse()
        return page, next_cursor, has_more


class FakeMessageBroker:
    """In-memory implementation of IMessageBroker collecting published events."""

    def __init__(self) -> None:
        self.published: List[Tuple[str, Any]] = []

    async def publish(self, channel: str, message: Any) -> None:
        self.published.append((channel, message))


# ──────────────────────────────────────────────
# Pytest & Test Fixtures
# ──────────────────────────────────────────────

@fixture
def fake_user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@fixture
def fake_room_repo() -> FakeRoomRepository:
    return FakeRoomRepository()


@fixture
def fake_message_repo() -> FakeMessageRepository:
    return FakeMessageRepository()


@fixture
def fake_broker() -> FakeMessageBroker:
    return FakeMessageBroker()


@fixture
def auth_service(fake_user_repo: FakeUserRepository) -> AuthService:
    return AuthService(fake_user_repo)


@fixture
def room_service(fake_room_repo: FakeRoomRepository) -> RoomService:
    return RoomService(fake_room_repo)


@fixture
def chat_service(
    fake_message_repo: FakeMessageRepository,
    fake_room_repo: FakeRoomRepository,
    fake_broker: FakeMessageBroker,
) -> ChatService:
    return ChatService(fake_message_repo, fake_room_repo, fake_broker)


@fixture
def test_client():
    """FastAPI TestClient with all repository and service dependencies overridden by in-memory fakes."""
    u_repo = FakeUserRepository()
    r_repo = FakeRoomRepository()
    m_repo = FakeMessageRepository()
    b_broker = FakeMessageBroker()

    a_service = AuthService(u_repo)
    rm_service = RoomService(r_repo)
    c_service = ChatService(m_repo, r_repo, b_broker)

    app.dependency_overrides[get_user_repository] = lambda: u_repo
    app.dependency_overrides[get_room_repository] = lambda: r_repo
    app.dependency_overrides[get_message_repository] = lambda: m_repo
    app.dependency_overrides[get_message_broker] = lambda: b_broker
    app.dependency_overrides[get_auth_service] = lambda: a_service
    app.dependency_overrides[get_room_service] = lambda: rm_service
    app.dependency_overrides[get_chat_service] = lambda: c_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
