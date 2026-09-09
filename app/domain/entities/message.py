from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MessageEntity:
    """Pure domain representation of a chat message.
    sender_username is a denormalized field populated by the repository
    to avoid N+1 queries in the application layer."""

    content: str
    room_id: int
    sender_id: int
    sender_username: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
