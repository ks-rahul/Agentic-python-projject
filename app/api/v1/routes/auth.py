"""Authentication routes."""
import secrets
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
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    from app.services.social_auth_service import SocialAuthService
    
    social_auth = SocialAuthService()
    
    try:
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Default redirect URI - should be configured per environment
        redirect_uri = f"{settings.APP_URL}/api/v1/auth/social/callback"
        
        result = social_auth.get_authorization_url(
            provider=request.provider,
            redirect_uri=redirect_uri,
            state=state
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/social/callback", response_model=TokenResponse)
async def social_callback(
    request: SocialAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback and authenticate user."""
    from app.services.social_auth_service import SocialAuthService
    
    if not request.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required"
        )
    
    social_auth = SocialAuthService()
    user_service = UserService(db)
    
    try:
        # Default redirect URI
        redirect_uri = f"{settings.APP_URL}/api/v1/auth/social/callback"
        
        # Authenticate with OAuth provider
        oauth_user = await social_auth.authenticate_user(
            provider=request.provider,
            code=request.code,
            redirect_uri=redirect_uri
        )
        
        if not oauth_user.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by OAuth provider"
            )
        
        # Check if user exists
        user = await user_service.get_by_email(oauth_user["email"])
        
        if not user:
            # Create new user from OAuth data
            user = await user_service.create(
                name=oauth_user.get("name", oauth_user["email"].split("@")[0]),
                email=oauth_user["email"],
                password=get_password_hash(secrets.token_urlsafe(32)),  # Random password
                profile_image=oauth_user.get("profile_image"),
                provider=oauth_user["provider"],
                provider_id=oauth_user["provider_id"],
                provider_token=oauth_user.get("access_token"),
                provider_refresh_token=oauth_user.get("refresh_token"),
                email_verified_at=datetime.now(timezone.utc)  # OAuth emails are verified
            )
        else:
            # Update existing user with OAuth info
            await user_service.update(
                str(user.id),
                provider=oauth_user["provider"],
                provider_id=oauth_user["provider_id"],
                provider_token=oauth_user.get("access_token"),
                provider_refresh_token=oauth_user.get("refresh_token")
            )
        
        # Get tenant_id
        tenant_id = None
        if user.tenants:
            tenant_id = str(user.tenants[0].id)
        
        # Generate tokens
        token_data = {"sub": str(user.id), "tenant_id": tenant_id}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Social auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Social authentication failed"
        )
