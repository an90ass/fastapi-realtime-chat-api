from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.message_model import MessageModel
    from app.infrastructure.persistence.models.user_model import UserModel


class RoomModel(Base):
    """SQLAlchemy ORM model for the rooms table."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_private: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    messages: Mapped[List["MessageModel"]] = relationship(
        "MessageModel", back_populates="room", cascade="all, delete-orphan"
    )
    members: Mapped[List["RoomMemberModel"]] = relationship(
        "RoomMemberModel", back_populates="room", cascade="all, delete-orphan"
    )


class RoomMemberModel(Base):
    """SQLAlchemy ORM model for the room_members table."""

    __tablename__ = "room_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room: Mapped["RoomModel"] = relationship("RoomModel", back_populates="members")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="memberships")

    __table_args__ = (
        Index("ix_room_user_unique", "room_id", "user_id", unique=True),
    )
