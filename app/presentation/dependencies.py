"""
Dependency Injection Container — the ONLY place where abstractions (Ports)
are bound to their concrete implementations (Adapters).

Layer flow (outer → inner, always pointing inward):
  Presentation (dependencies.py)
    → Application Services (use cases)
    → Domain Ports (IUserRepository, IRoomRepository, etc.)
    ← Infrastructure adapters implement the ports (injected here)

This file is the "Composition Root" of the application.
It knows about ALL layers but no other file does.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthService
from app.application.services.chat_service import ChatService
from app.application.services.room_service import RoomService
from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.domain.entities.user import UserEntity
from app.domain.ports.message_broker import IMessageBroker
from app.domain.ports.repositories import IMessageRepository, IRoomRepository, IUserRepository
from app.infrastructure.messaging.redis_broker import RedisMessageBroker
from app.infrastructure.persistence.repositories.message_repository import SqlAlchemyMessageRepository
from app.infrastructure.persistence.repositories.room_repository import SqlAlchemyRoomRepository
from app.infrastructure.persistence.repositories.user_repository import SqlAlchemyUserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Singleton broker — created once, reused across all requests ──
_redis_broker: RedisMessageBroker = RedisMessageBroker()


# ──────────────────────────────────────────────
# Repository Providers (bind ports → adapters)
# ──────────────────────────────────────────────

def get_user_repository(db: AsyncSession = Depends(get_db)) -> IUserRepository:
    return SqlAlchemyUserRepository(db)


def get_room_repository(db: AsyncSession = Depends(get_db)) -> IRoomRepository:
    return SqlAlchemyRoomRepository(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> IMessageRepository:
    return SqlAlchemyMessageRepository(db)


# ──────────────────────────────────────────────
# Message Broker Provider (bind port → adapter)
# ──────────────────────────────────────────────

def get_message_broker() -> IMessageBroker:
    return _redis_broker


# ──────────────────────────────────────────────
# Service / Use-Case Providers
# ──────────────────────────────────────────────

def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(user_repo)


def get_room_service(
    room_repo: IRoomRepository = Depends(get_room_repository),
) -> RoomService:
    return RoomService(room_repo)


def get_chat_service(
    message_repo: IMessageRepository = Depends(get_message_repository),
    room_repo: IRoomRepository = Depends(get_room_repository),
    broker: IMessageBroker = Depends(get_message_broker),
) -> ChatService:
    return ChatService(message_repo, room_repo, broker)


# ──────────────────────────────────────────────
# Auth Guard
# ──────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserEntity:
    """FastAPI dependency that validates JWT and returns the active UserEntity."""
    try:
        return await auth_service.get_user_from_token(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
