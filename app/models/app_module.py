"""App Module model for permission grouping."""
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AppModule(BaseModel):
    """App Module model for organizing permissions by feature area."""
    __tablename__ = "app_modules"

    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    permissions = relationship("Permission", back_populates="app_module")
