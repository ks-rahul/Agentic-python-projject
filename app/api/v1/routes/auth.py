"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.db.postgresql import get_db
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, UpdatePasswordRequest, SocialAuthRequest
)
from app.schemas.user import UserResponse
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, decode_token, get_current_user
)
from app.services.user_service import UserService
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return tokens."""
    user_service = UserService(db)
    user = await user_service.get_by_email(request.email)
    
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    # Get tenant_id
    tenant_id = None
    if user.tenants:
        tenant_id = str(user.tenants[0].id)
    
    token_data = {"sub": str(user.id), "tenant_id": tenant_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    user_service = UserService(db)
    
    # Check if email exists
    existing_user = await user_service.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await user_service.create(
        name=request.name,
        email=request.email,
        password=get_password_hash(request.password),
        phone=request.phone,
        country_code=request.country_code
    )
    
    # TODO: Send verification email
    
    return user


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate token on client side)."""
    # In a stateless JWT system, logout is handled client-side
    # For server-side invalidation, implement token blacklisting
    return {"message": "Successfully logged out"}


@router.post("/email/verify/resend")
async def resend_verification_email(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Resend email verification link."""
    user_service = UserService(db)
    user = await user_service.get_by_email(email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # TODO: Generate and send verification email
    
    return {"message": "Verification email sent"}


@router.get("/email/verify/{user_id}/{hash}")
async def verify_email(
    user_id: str,
    hash: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email."""
    user_service = UserService(db)
    
    # TODO: Verify hash and update user
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user_service.update(user_id, email_verified_at=datetime.now(timezone.utc))
    
    return {"message": "Email verified successfully"}


@router.post("/password/forgot")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset email."""
    user_service = UserService(db)
    user = await user_service.get_by_email(request.email)
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # TODO: Generate reset token and send email
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password/update")
async def update_password(
    request: UpdatePasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update password using reset token."""
    if request.password != request.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    user_service = UserService(db)
    
    # TODO: Verify reset token
    user = await user_service.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user_service.update(user.id, password=get_password_hash(request.password))
    
    return {"message": "Password updated successfully"}


@router.post("/social/redirect")
async def social_redirect(request: SocialAuthRequest):
    """Get OAuth redirect URL for social login."""
    # TODO: Implement OAuth redirect URL generation
    return {"redirect_url": f"https://oauth.provider.com/{request.provider}"}


@router.post("/social/callback", response_model=TokenResponse)
async def social_callback(
    request: SocialAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback and authenticate user."""
    user_service = UserService(db)
    
    # TODO: Verify OAuth token with provider and get user info
    # For now, this is a placeholder
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Social authentication not yet implemented"
    )
