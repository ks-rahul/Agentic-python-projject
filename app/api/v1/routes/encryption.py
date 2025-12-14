"""Encryption and key handshake routes for secure chat communication."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.session_service import SessionService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HandshakeRequest(BaseModel):
    session_id: str


class HandshakeResponse(BaseModel):
    success: bool
    encryption_key: str
    session_id: str
    encryption_enabled: bool
    timestamp: str
    message: str


@router.post("/handshake", response_model=HandshakeResponse)
async def initiate_key_handshake(request: HandshakeRequest):
    """
    Initiate key handshake - share server's AES key with client.
    This enables end-to-end encryption for chat messages.
    """
    session_service = SessionService()
    
    # Check if session exists
    session = await session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get the AES key from server configuration
    aes_key = settings.ENCRYPTION_KEY
    if not aes_key:
        logger.error("Server AES key not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server encryption not configured"
        )
    
    # Update session with encryption key
    await session_service.update_session_encryption(
        request.session_id,
        {
            "encryption_key": aes_key,
            "key_shared_at": datetime.utcnow()
        }
    )
    
    logger.info(f"Key handshake completed for session {request.session_id}")
    
    return HandshakeResponse(
        success=True,
        encryption_key=aes_key,
        session_id=request.session_id,
        encryption_enabled=True,
        timestamp=datetime.utcnow().isoformat(),
        message="Key handshake successful, AES key shared for encryption"
    )


@router.get("/public-key")
async def get_server_public_key():
    """
    Get server encryption info.
    Returns information about the encryption type used.
    """
    return {
        "success": True,
        "encryption_type": "AES-256-GCM",
        "message": "Server uses AES encryption. Use handshake endpoint to get encryption key.",
        "timestamp": datetime.utcnow().isoformat()
    }
