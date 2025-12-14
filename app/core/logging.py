"""Logging configuration with API request logging and audit trails."""
import logging
import sys
import time
import json
import os
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Log directory and settings
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))  # Days to keep logs


def setup_logging():
    """Configure structured logging with daily file rotation and auto-cleanup."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Create logs directory if it doesn't exist
    if LOG_TO_FILE and not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File formatter
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handlers (if enabled) - All daily rotation
    if LOG_TO_FILE:
        # Main application log (daily rotation)
        app_file_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "app.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS
        )
        app_file_handler.suffix = "%Y-%m-%d"
        app_file_handler.setLevel(log_level)
        app_file_handler.setFormatter(file_formatter)
        root_logger.addHandler(app_file_handler)
        
        # Error log (daily rotation)
        error_file_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "error.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS
        )
        error_file_handler.suffix = "%Y-%m-%d"
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_file_handler)
        
        # Audit log (daily rotation)
        audit_file_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "audit.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS
        )
        audit_file_handler.suffix = "%Y-%m-%d"
        audit_file_handler.setLevel(logging.INFO)
        audit_file_handler.setFormatter(file_formatter)
        logging.getLogger("audit").addHandler(audit_file_handler)
        
        # Security log (daily rotation)
        security_file_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "security.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS
        )
        security_file_handler.suffix = "%Y-%m-%d"
        security_file_handler.setLevel(logging.INFO)
        security_file_handler.setFormatter(file_formatter)
        logging.getLogger("security").addHandler(security_file_handler)
        
        # API request log (daily rotation)
        api_file_handler = TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "api.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS
        )
        api_file_handler.suffix = "%Y-%m-%d"
        api_file_handler.setLevel(logging.INFO)
        api_file_handler.setFormatter(file_formatter)
        logging.getLogger("api").addHandler(api_file_handler)

    # Configure structlog - use KeyValueRenderer for clean file output
    # This removes ANSI color codes from logs
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use KeyValueRenderer for clean logs (no colors)
            structlog.processors.KeyValueRenderer(
                key_order=["timestamp", "level", "logger", "event"],
                drop_missing=True
            ),
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
