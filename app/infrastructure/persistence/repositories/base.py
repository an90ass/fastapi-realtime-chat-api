"""
Shared SQLAlchemy async helpers for concrete repository implementations.
This base class operates on ORM models only — it is a pure infrastructure utility.
"""

from typing import Any, Generic, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

OrmModelType = TypeVar("OrmModelType")


class BaseSqlAlchemyRepository(Generic[OrmModelType]):
    """Generic infrastructure base providing reusable async ORM operations."""

    def __init__(self, model: Type[OrmModelType], db: AsyncSession) -> None:
        self._model = model
        self._db = db

    async def _get_by_id(self, entity_id: Any) -> Optional[OrmModelType]:
        result = await self._db.execute(
            select(self._model).where(self._model.id == entity_id)
        )
        return result.scalars().first()

    async def _persist(self, orm_instance: OrmModelType) -> OrmModelType:
        self._db.add(orm_instance)
        await self._db.commit()
        await self._db.refresh(orm_instance)
        return orm_instance

    async def _delete(self, orm_instance: OrmModelType) -> None:
        await self._db.delete(orm_instance)
        await self._db.commit()
