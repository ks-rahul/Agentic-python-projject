"""Base service class with common CRUD operations."""
from typing import TypeVar, Generic, Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.db.postgresql import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseService(Generic[ModelType]):
    """Base service with common CRUD operations."""
    
    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model
    
    async def get_by_id(self, id: str, load_relations: List[str] = None) -> Optional[ModelType]:
        """Get record by ID."""
        query = select(self.model).where(self.model.id == id)
        
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update a record."""
        # Remove None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        return await self.get_by_id(id)
    
    async def delete(self, id: str) -> bool:
        """Soft delete a record."""
        if hasattr(self.model, 'deleted_at'):
            await self.update(id, deleted_at=datetime.utcnow())
        else:
            query = delete(self.model).where(self.model.id == id)
            await self.db.execute(query)
            await self.db.commit()
        return True
    
    async def hard_delete(self, id: str) -> bool:
        """Permanently delete a record."""
        query = delete(self.model).where(self.model.id == id)
        await self.db.execute(query)
        await self.db.commit()
        return True
