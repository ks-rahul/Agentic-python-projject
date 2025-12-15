"""Authentication routes."""
import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.db.postgresql import get_db
from app.db.redis import get_redis
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
from app.services.tenant_service import TenantService
from app.tasks.email_tasks import (
    send_verification_email_task,
    send_password_reset_email_task,
    send_welcome_email_task
)
from app.tasks.notification_tasks import (
    notify_user_registered_task,
    notify_password_changed_task
)
from app.core.config import settings
from app.core.logging import get_logger, audit

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return tokens."""
    user_service = UserService(db)
    user = await user_service.get_by_email(request.email)
    client_ip = req.client.host if req.client else "unknown"
    
    if not user or not verify_password(request.password, user.password):
        # Log failed login attempt
        audit.log_login(
            user_id=str(user.id) if user else "unknown",
            email=request.email,
            ip_address=client_ip,
            success=False,
            reason="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "active":
        audit.log_login(
            user_id=str(user.id),
            email=request.email,
            ip_address=client_ip,
            success=False,
            reason="Account not active"
        )
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
    
    # Log successful login
    audit.log_login(
        user_id=str(user.id),
        email=request.email,
        ip_address=client_ip,
        success=True
    )
    
    logger.info("user_logged_in", user_id=str(user.id), email=request.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    user_service = UserService(db)
    client_ip = req.client.host if req.client else "unknown"
    
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

    # Create tenant
    tenant_service = TenantService(db)
    await tenant_service.create_with_user(user.id, user.name)
    
    # Generate verification token and store in Redis
    verification_token = secrets.token_urlsafe(32)
    verification_hash = hashlib.sha256(verification_token.encode()).hexdigest()
    
    redis = await get_redis()
    await redis.setex(
        f"email_verify:{str(user.id)}",
        86400,  # 24 hours
        verification_hash
    )
    
    # Send verification email (async via Celery)
    verification_url = f"{settings.FRONTEND_URL}/email/verify/{user.id}/{verification_token}"
    send_verification_email_task.delay(
        email=user.email,
        name=user.name,
        verification_url=verification_url
    )
    
    # Send welcome notification (async via Celery)
    notify_user_registered_task.delay(
        user_id=str(user.id),
        name=user.name,
        email=user.email
    )
    
    # Audit log
    audit.log_action(
        action="user_registered",
        user_id=str(user.id),
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "name": user.name},
        ip_address=client_ip
    )
    
    logger.info("user_registered", user_id=str(user.id), email=user.email)
    
    return user


@router.post("/logout")
async def logout(req: Request, current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate token on client side)."""
    client_ip = req.client.host if req.client else "unknown"
    user_id = current_user.get("sub", "unknown")
    
    # Log logout
    audit.log_logout(user_id=user_id, ip_address=client_ip)
    logger.info("user_logged_out", user_id=user_id)
    
    # Optionally blacklist the token in Redis
    # token = req.headers.get("Authorization", "").replace("Bearer ", "")
    # redis = await get_redis()
    # await redis.setex(f"blacklist:{token}", settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
    
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
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    verification_hash = hashlib.sha256(verification_token.encode()).hexdigest()
    
    redis = await get_redis()
    await redis.setex(
        f"email_verify:{str(user.id)}",
        86400,  # 24 hours
        verification_hash
    )
    
    # Send verification email (async via Celery)
    verification_url = f"{settings.APP_URL}/api/v1/auth/email/verify/{user.id}/{verification_token}"
    send_verification_email_task.delay(
        email=user.email,
        name=user.name,
        verification_url=verification_url
    )
    
    logger.info("verification_email_resent", user_id=str(user.id), email=email)
    
    return {"message": "Verification email sent"}


@router.get("/email/verify/{user_id}/{token}")
async def verify_email(
    user_id: str,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email."""
    user_service = UserService(db)
    
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified_at:
        return {"message": "Email already verified"}
    
    # Verify token from Redis
    redis = await get_redis()
    stored_hash = await redis.get(f"email_verify:{user_id}")
    
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link expired"
        )
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash != stored_hash.decode() if isinstance(stored_hash, bytes) else stored_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification link"
        )
    
    # Update user
    await user_service.update(user_id, email_verified_at=datetime.now(timezone.utc))
    
    # Delete verification token
    await redis.delete(f"email_verify:{user_id}")
    
    # Send welcome email (async via Celery)
    send_welcome_email_task.delay(email=user.email, name=user.name)
    
    logger.info("email_verified", user_id=user_id, email=user.email)
    
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
        # Don't reveal if email exists - but still return same message
        logger.info("password_reset_requested_unknown_email", email=request.email)
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    
    # Store in Redis with 1 hour expiry
    redis = await get_redis()
    await redis.setex(
        f"password_reset:{str(user.id)}",
        3600,  # 1 hour
        reset_hash
    )
    
    # Send password reset email (async via Celery)
    reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}&email={user.email}"
    send_password_reset_email_task.delay(
        email=user.email,
        name=user.name,
        reset_url=reset_url
    )
    
    logger.info("password_reset_email_sent", user_id=str(user.id), email=user.email)
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password/update")
async def update_password(
    request: UpdatePasswordRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update password using reset token."""
    client_ip = req.client.host if req.client else "unknown"
    
    if request.password != request.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    user_service = UserService(db)
    user = await user_service.get_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify reset token from Redis
    redis = await get_redis()
    stored_hash = await redis.get(f"password_reset:{str(user.id)}")
    
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link expired or invalid"
        )
    
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    stored_hash_str = stored_hash.decode() if isinstance(stored_hash, bytes) else stored_hash
    
    if token_hash != stored_hash_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    # Update password
    await user_service.update(str(user.id), password=get_password_hash(request.password))
    
    # Delete reset token
    await redis.delete(f"password_reset:{str(user.id)}")
    
    # Log password change
    audit.log_password_change(user_id=str(user.id), ip_address=client_ip)
    
    # Notify user (async via Celery)
    notify_password_changed_task.delay(
        user_id=str(user.id),
        email=user.email
    )
    
    logger.info("password_updated", user_id=str(user.id), email=user.email)
    
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
            # Use token_hex(24) to generate 48 char password (within bcrypt's 72 byte limit)
            user = await user_service.create(
                name=oauth_user.get("name", oauth_user["email"].split("@")[0]),
                email=oauth_user["email"],
                password=get_password_hash(secrets.token_hex(24)),  # Random password (48 chars)
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
