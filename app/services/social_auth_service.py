"""Social authentication service for OAuth providers."""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SocialAuthService:
    """Service for handling social authentication with OAuth providers."""
    
    # OAuth provider configurations
    PROVIDERS = {
        "google": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": ["openid", "email", "profile"],
        },
        "github": {
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scopes": ["user:email", "read:user"],
        },
        "microsoft": {
            "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me",
            "scopes": ["openid", "email", "profile", "User.Read"],
        },
        "facebook": {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "userinfo_url": "https://graph.facebook.com/me?fields=id,name,email,picture",
            "scopes": ["email", "public_profile"],
        },
    }
    
    def __init__(self):
        self.client_ids = {
            "google": settings.GOOGLE_CLIENT_ID,
            "github": settings.GITHUB_CLIENT_ID,
            "microsoft": settings.MICROSOFT_CLIENT_ID,
            "facebook": settings.FACEBOOK_CLIENT_ID,
        }
        self.client_secrets = {
            "google": settings.GOOGLE_CLIENT_SECRET,
            "github": settings.GITHUB_CLIENT_SECRET,
            "microsoft": settings.MICROSOFT_CLIENT_SECRET,
            "facebook": settings.FACEBOOK_CLIENT_SECRET,
        }
    
    def get_authorization_url(
        self,
        provider: str,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate OAuth authorization URL for a provider."""
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.PROVIDERS[provider]
        client_id = self.client_ids.get(provider)
        
        if not client_id:
            raise ValueError(f"Client ID not configured for {provider}")
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
        }
        
        if state:
            params["state"] = state
        
        # Provider-specific parameters
        if provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        
        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        
        return {
            "redirect_url": auth_url,
            "provider": provider,
            "state": state
        }
    
    async def exchange_code_for_token(
        self,
        provider: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.PROVIDERS[provider]
        client_id = self.client_ids.get(provider)
        client_secret = self.client_secrets.get(provider)
        
        if not client_id or not client_secret:
            raise ValueError(f"OAuth credentials not configured for {provider}")
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data=data,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Failed to exchange code for token: {response.text}")
            
            return response.json()
    
    async def get_user_info(
        self,
        provider: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Get user information from OAuth provider."""
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.PROVIDERS[provider]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # GitHub uses different header format
        if provider == "github":
            headers["Accept"] = "application/vnd.github.v3+json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                config["userinfo_url"],
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise ValueError(f"Failed to get user info: {response.text}")
            
            user_data = response.json()
            
            # Normalize user data across providers
            return self._normalize_user_data(provider, user_data)
    
    def _normalize_user_data(
        self,
        provider: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize user data from different providers to a common format."""
        normalized = {
            "provider": provider,
            "provider_id": None,
            "email": None,
            "name": None,
            "profile_image": None,
        }
        
        if provider == "google":
            normalized["provider_id"] = data.get("id")
            normalized["email"] = data.get("email")
            normalized["name"] = data.get("name")
            normalized["profile_image"] = data.get("picture")
        
        elif provider == "github":
            normalized["provider_id"] = str(data.get("id"))
            normalized["email"] = data.get("email")
            normalized["name"] = data.get("name") or data.get("login")
            normalized["profile_image"] = data.get("avatar_url")
        
        elif provider == "microsoft":
            normalized["provider_id"] = data.get("id")
            normalized["email"] = data.get("mail") or data.get("userPrincipalName")
            normalized["name"] = data.get("displayName")
            # Microsoft Graph doesn't return profile image directly
        
        elif provider == "facebook":
            normalized["provider_id"] = data.get("id")
            normalized["email"] = data.get("email")
            normalized["name"] = data.get("name")
            picture = data.get("picture", {}).get("data", {})
            normalized["profile_image"] = picture.get("url")
        
        return normalized
    
    async def authenticate_user(
        self,
        provider: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Complete OAuth flow and return user information."""
        # Exchange code for token
        token_data = await self.exchange_code_for_token(provider, code, redirect_uri)
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise ValueError("No access token received")
        
        # Get user info
        user_info = await self.get_user_info(provider, access_token)
        
        # Add tokens to user info
        user_info["access_token"] = access_token
        user_info["refresh_token"] = refresh_token
        user_info["token_expires_in"] = token_data.get("expires_in")
        
        return user_info
