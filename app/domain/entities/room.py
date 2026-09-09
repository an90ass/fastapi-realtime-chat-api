from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RoomEntity:
    """Pure domain representation of a chat room."""

    name: str
    id: Optional[int] = None
    description: Optional[str] = None
    is_private: bool = False
    created_at: Optional[datetime] = None


@dataclass
class RoomMemberEntity:
    """Pure domain representation of a room membership record."""

    room_id: int
    user_id: int
    id: Optional[int] = None
    joined_at: Optional[datetime] = None
