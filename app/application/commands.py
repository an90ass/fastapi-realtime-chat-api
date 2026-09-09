"""
Application-layer Command and Result objects.
These are simple, immutable data transfer objects that act as the
boundary between the Presentation layer and the Application Use Cases.

Using Commands enforces CQRS-lite: callers pass explicit intents
(what they want to do) rather than raw framework request objects,
keeping Use Cases fully independent of FastAPI/Pydantic.
"""

from dataclasses import dataclass
from typing import Optional


# ──────────────────────────────────────────────
# Auth Commands
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class RegisterUserCommand:
    username: str
    email: str
    password: str


@dataclass(frozen=True)
class AuthenticateUserCommand:
    email: str
    password: str


# ──────────────────────────────────────────────
# Auth Results (Value Objects)
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class AuthTokenResult:
    access_token: str
    token_type: str = "bearer"


# ──────────────────────────────────────────────
# Room Commands
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class CreateRoomCommand:
    name: str
    creator_id: int
    description: Optional[str] = None
    is_private: bool = False


# ──────────────────────────────────────────────
# Message Results
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class MessagePageResult:
    """Paginated message list returned by the ChatService use case."""
    items: tuple          # Tuple[MessageEntity, ...]
    next_cursor: Optional[int]
    has_more: bool
