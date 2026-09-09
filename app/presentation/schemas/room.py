from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RoomCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_private: bool = False


class RoomResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_private: bool
    created_at: Optional[datetime] = None


class RoomMemberResponseSchema(BaseModel):
    id: int
    room_id: int
    user_id: int
    joined_at: Optional[datetime] = None
