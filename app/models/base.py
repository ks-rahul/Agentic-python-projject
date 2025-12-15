"""Base model with common fields."""
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, CHAR
from sqlalchemy.types import TypeDecorator

from app.db.mysql import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type using CHAR(36) for MySQL."""
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


class BaseModel(Base):
    """Abstract base model with UUID and timestamps."""
    __abstract__ = True

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
