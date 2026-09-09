from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models.
    Lives exclusively in the infrastructure layer."""
    pass
