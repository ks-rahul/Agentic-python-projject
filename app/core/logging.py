"""Logging configuration with API request logging and audit trails."""
import logging
import sys
import time
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from functools import wraps
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.APP_ENV == "production" 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# API Request Logger
api_logger = get_logger("api")
audit_logger = get_logger("audit")
security_logger = get_logger("security")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all API requests."""
    
    SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key"}
    SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "access_token", "refresh_token"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            self._log_response(request, response, process_time, request_id)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            self._log_error(request, e, process_time, request_id)
            raise
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request."""
        # Sanitize headers
        headers = {
            k: "[REDACTED]" if k.lower() in self.SENSITIVE_HEADERS else v
            for k, v in request.headers.items()
        }
        
        api_logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            headers=headers if settings.DEBUG else None
        )
    
    def _log_response(self, request: Request, response: Response, process_time: float, request_id: str):
        """Log response."""
        log_level = "info" if response.status_code < 400 else "warning" if response.status_code < 500 else "error"
        
        getattr(api_logger, log_level)(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2)
        )
    
    def _log_error(self, request: Request, error: Exception, process_time: float, request_id: str):
        """Log error."""
        api_logger.error(
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            error=str(error),
            error_type=type(error).__name__,
            process_time_ms=round(process_time * 1000, 2)
        )


class AuditLogger:
    """Audit logger for tracking important actions."""
    
    @staticmethod
    def log_action(
        action: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log an auditable action."""
        audit_logger.info(
            "audit_event",
            action=action,
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @staticmethod
    def log_login(user_id: str, email: str, ip_address: str, success: bool, reason: str = None):
        """Log login attempt."""
        event = "login_success" if success else "login_failed"
        security_logger.info(
            event,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @staticmethod
    def log_logout(user_id: str, ip_address: str):
        """Log logout."""
        security_logger.info(
            "logout",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @staticmethod
    def log_password_change(user_id: str, ip_address: str):
        """Log password change."""
        security_logger.info(
            "password_changed",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    @staticmethod
    def log_permission_change(
        user_id: str,
        target_user_id: str,
        action: str,
        permissions: list,
        ip_address: str
    ):
        """Log permission changes."""
        security_logger.info(
            "permission_change",
            user_id=user_id,
            target_user_id=target_user_id,
            action=action,
            permissions=permissions,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


def log_function_call(logger_name: str = None):
    """Decorator to log function calls."""
    def decorator(func: Callable):
        _logger = get_logger(logger_name or func.__module__)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            _logger.debug(f"calling_{func.__name__}", args_count=len(args), kwargs_keys=list(kwargs.keys()))
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                _logger.debug(f"completed_{func.__name__}", elapsed_ms=round(elapsed * 1000, 2))
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(f"failed_{func.__name__}", error=str(e), elapsed_ms=round(elapsed * 1000, 2))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            _logger.debug(f"calling_{func.__name__}", args_count=len(args), kwargs_keys=list(kwargs.keys()))
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                _logger.debug(f"completed_{func.__name__}", elapsed_ms=round(elapsed * 1000, 2))
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(f"failed_{func.__name__}", error=str(e), elapsed_ms=round(elapsed * 1000, 2))
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Export audit logger instance
audit = AuditLogger()
