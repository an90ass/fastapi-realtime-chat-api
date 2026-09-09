from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.message_model import MessageModel
    from app.infrastructure.persistence.models.room_model import RoomMemberModel


class UserModel(Base):
    """SQLAlchemy ORM model for the users table.
    This is a pure infrastructure concern — never referenced by Application or Domain layers."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    messages: Mapped[List["MessageModel"]] = relationship(
        "MessageModel", back_populates="sender", cascade="all, delete-orphan"
    )
    memberships: Mapped[List["RoomMemberModel"]] = relationship(
        "RoomMemberModel", back_populates="user", cascade="all, delete-orphan"
    )
