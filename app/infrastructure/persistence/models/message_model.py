from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.room_model import RoomModel
    from app.infrastructure.persistence.models.user_model import UserModel


class MessageModel(Base):
    """SQLAlchemy ORM model for the messages table.
    Includes a composite index on (room_id, id) for ultra-fast cursor pagination."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room: Mapped["RoomModel"] = relationship("RoomModel", back_populates="messages")
    sender: Mapped["UserModel"] = relationship("UserModel", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_room_id_id", "room_id", "id"),
    )
