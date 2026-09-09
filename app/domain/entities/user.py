from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserEntity:
    """Pure domain representation of a registered user.
    Contains no ORM/framework dependencies — only business-relevant data."""

    username: str
    email: str
    hashed_password: str
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
