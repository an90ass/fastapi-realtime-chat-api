from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageResponseSchema(BaseModel):
    id: int
    content: str
    room_id: int
    sender_id: int
    username: Optional[str] = None
    created_at: Optional[datetime] = None


class MessageCursorPageSchema(BaseModel):
    items: List[MessageResponseSchema]
    next_cursor: Optional[int] = None
    has_more: bool = False


class WebSocketInSchema(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class WebSocketOutSchema(BaseModel):
    id: int
    content: str
    room_id: int
    sender_id: int
    username: str
    created_at: str
