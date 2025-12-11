"""User service for user management."""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.tenant import TenantUser
from app.services.base_service import BaseService


class UserService(BaseService[User]):
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.tenants))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """List users with filtering and pagination."""
        query = select(User).where(User.deleted_at.is_(None))
        count_query = select(func.count(User.id)).where(User.deleted_at.is_(None))
        
        # Filter by tenant
        if tenant_id:
            query = query.join(TenantUser).where(TenantUser.tenant_id == tenant_id)
            count_query = count_query.join(TenantUser).where(TenantUser.tenant_id == tenant_id)
        
        # Search filter
        if search:
            search_filter = or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Status filter
        if status:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute queries
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return users, total
    
    async def create(
        self,
        name: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
        country_code: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> User:
        """Create a new user."""
        user = await super().create(
            name=name,
            email=email,
            password=password,
            phone=phone,
            country_code=country_code
        )
        
        # Associate with tenant if provided
        if tenant_id:
            tenant_user = TenantUser(tenant_id=tenant_id, user_id=user.id)
            self.db.add(tenant_user)
            await self.db.commit()
        
        return user
