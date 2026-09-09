from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: str
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
