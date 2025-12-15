"""User management routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, ProfileUpdateRequest
)
from app.services.user_service import UserService
from app.core.security import get_current_user, get_password_hash

router = APIRouter()


@router.get("/list", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all users with pagination."""
    user_service = UserService(db)
    users, total = await user_service.list_users(
        page=page,
        per_page=per_page,
        search=search,
        status=status,
        tenant_id=current_user.get("tenant_id")
    )
    
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/get/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user by ID."""
    user_service = UserService(db)
    user = await user_service.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new user."""
    user_service = UserService(db)
    
    # Check if email exists
    existing_user = await user_service.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await user_service.create(
        name=request.name,
        email=request.email,
        password=get_password_hash(request.password),
        phone=request.phone,
        country_code=request.country_code,
        tenant_id=current_user.get("tenant_id")
    )
    
    return user


@router.post("/update/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user."""
    user_service = UserService(db)
    
    user = await user_service.get_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user = await user_service.update(
        str(user_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_user


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete user (soft delete)."""
    user_service = UserService(db)
    
    user = await user_service.get_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user_service.delete(str(user_id))
    return None


@router.patch("/toggle-status/{user_id}")
async def toggle_user_status(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Toggle user active status."""
    user_service = UserService(db)
    
    user = await user_service.get_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    new_status = "inactive" if user.status == "active" else "active"
    await user_service.update(str(user_id), status=new_status)
    
    return {"message": f"User status changed to {new_status}"}


@router.post("/profile/update/{user_id}", response_model=UserResponse)
async def update_profile(
    user_id: UUID,
    request: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user profile."""
    user_service = UserService(db)
    
    user = await user_service.get_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_user = await user_service.update(
        str(user_id),
        **request.model_dump(exclude_unset=True)
    )
    
    return updated_user
