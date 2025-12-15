"""Health check and metrics routes."""
import time
import psutil
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.db.mysql import get_db
from app.db.mongodb import get_mongodb
from app.db.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
metrics_router = APIRouter()

# Track server start time
SERVER_START_TIME = time.time()


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - SERVER_START_TIME,
        "memory": _get_memory_usage(),
        "environment": "production"
    }


@router.get("/deep")
async def deep_health_check(db=Depends(get_db)):
    """Deep health check including database and cache connectivity."""
    checks = {
        "api": "healthy",
        "database": "checking",
        "mongodb": "checking",
        "cache": "checking",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check MySQL
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = "unhealthy"
        checks["database_error"] = str(e)
    
    # Check MongoDB
    try:
        mongo_client = await get_mongodb()
        await mongo_client.admin.command('ping')
        checks["mongodb"] = "healthy"
    except Exception as e:
        checks["mongodb"] = "unhealthy"
        checks["mongodb_error"] = str(e)
    
    # Check Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        checks["cache"] = "healthy"
    except Exception as e:
        checks["cache"] = "unhealthy"
        checks["cache_error"] = str(e)
    
    is_healthy = all(
        checks.get(k) == "healthy" 
        for k in ["database", "mongodb", "cache"]
    )
    
    checks["status"] = "healthy" if is_healthy else "unhealthy"
    checks["uptime"] = time.time() - SERVER_START_TIME
    checks["memory"] = _get_memory_usage()
    
    return checks


@router.get("/ready")
async def readiness_check(db=Depends(get_db)):
    """Readiness check - indicates if service is ready to accept traffic."""
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        
        mongo_client = await get_mongodb()
        await mongo_client.admin.command('ping')
        
        redis_client = await get_redis()
        await redis_client.ping()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/live")
async def liveness_check():
    """Liveness check - indicates if service is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - SERVER_START_TIME
    }


# Metrics endpoints
@metrics_router.get("")
async def get_metrics():
    """Get system metrics."""
    from app.services.session_service import SessionService
    
    session_service = SessionService()
    
    try:
        session_stats = await session_service.get_session_stats()
    except:
        session_stats = {"active": 0, "total": 0}
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - SERVER_START_TIME,
        "memory": _get_memory_usage(),
        "cpu": _get_cpu_usage(),
        "sessions": session_stats
    }


@metrics_router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get Prometheus-style metrics."""
    from app.services.session_service import SessionService
    
    session_service = SessionService()
    
    try:
        stats = await session_service.get_session_stats()
        active_sessions = stats.get("active", 0)
        total_sessions = stats.get("total", 0)
    except:
        active_sessions = 0
        total_sessions = 0
    
    memory = _get_memory_usage()
    timestamp = int(time.time() * 1000)
    
    metrics = f"""
# HELP chat_sessions_active Number of active chat sessions
# TYPE chat_sessions_active gauge
chat_sessions_active {active_sessions} {timestamp}

# HELP chat_sessions_total Total number of chat sessions
# TYPE chat_sessions_total counter
chat_sessions_total {total_sessions} {timestamp}

# HELP python_memory_usage_bytes Python memory usage in bytes
# TYPE python_memory_usage_bytes gauge
python_memory_usage_bytes{{type="rss"}} {memory.get('rss', 0)} {timestamp}
python_memory_usage_bytes{{type="vms"}} {memory.get('vms', 0)} {timestamp}
python_memory_usage_bytes{{type="percent"}} {memory.get('percent', 0)} {timestamp}

# HELP python_process_uptime_seconds Python process uptime in seconds
# TYPE python_process_uptime_seconds gauge
python_process_uptime_seconds {time.time() - SERVER_START_TIME} {timestamp}
    """.strip()
    
    return metrics


@metrics_router.get("/sessions")
async def get_session_stats(time_range: str = "24h"):
    """Get session statistics."""
    from app.services.session_service import SessionService
    
    session_service = SessionService()
    stats = await session_service.get_session_stats(time_range)
    
    return {
        "time_range": time_range,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@metrics_router.get("/messages")
async def get_message_stats(time_range: str = "24h"):
    """Get message statistics."""
    from app.services.session_service import SessionService
    
    session_service = SessionService()
    stats = await session_service.get_message_stats(time_range)
    
    return {
        "time_range": time_range,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


def _get_memory_usage() -> dict:
    """Get current memory usage."""
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "percent": process.memory_percent()
        }
    except:
        return {"rss": 0, "vms": 0, "percent": 0}


def _get_cpu_usage() -> dict:
    """Get current CPU usage."""
    try:
        process = psutil.Process()
        return {
            "percent": process.cpu_percent(interval=0.1),
            "num_threads": process.num_threads()
        }
    except:
        return {"percent": 0, "num_threads": 0}
