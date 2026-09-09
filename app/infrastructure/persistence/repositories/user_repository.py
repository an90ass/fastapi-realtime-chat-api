"""
SqlAlchemyUserRepository — concrete implementation of IUserRepository.

Responsibilities:
  1. Execute async SQLAlchemy queries against the users table.
  2. Map ORM UserModel ↔ Domain UserEntity (Anti-Corruption Layer).

Implements: app.domain.ports.repositories.IUserRepository (structurally, via Protocol).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import UserEntity
from app.infrastructure.persistence.models.user_model import UserModel
from app.infrastructure.persistence.repositories.base import BaseSqlAlchemyRepository


def _to_entity(model: UserModel) -> UserEntity:
    """Map ORM model → Domain entity (Anti-Corruption Layer)."""
    return UserEntity(
        id=model.id,
        username=model.username,
        email=model.email,
        hashed_password=model.hashed_password,
        is_active=bool(model.is_active),
        created_at=model.created_at,
    )


class SqlAlchemyUserRepository(BaseSqlAlchemyRepository[UserModel]):
    """Concrete async user repository. Implements IUserRepository protocol."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(UserModel, db)

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        model = await self._get_by_id(user_id)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        result = await self._db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalars().first()
        return _to_entity(model) if model else None

    async def get_by_username(self, username: str) -> Optional[UserEntity]:
        result = await self._db.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalars().first()
        return _to_entity(model) if model else None

    async def create(self, entity: UserEntity) -> UserEntity:
        orm = UserModel(
            username=entity.username,
            email=entity.email,
            hashed_password=entity.hashed_password,
            is_active=entity.is_active,
        )
        saved = await self._persist(orm)
        return _to_entity(saved)
