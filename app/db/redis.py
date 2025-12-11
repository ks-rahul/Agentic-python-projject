"""Redis connection for caching."""
import redis.asyncio as redis
from typing import Optional
import json

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    client: Optional[redis.Redis] = None


redis_client = RedisClient()


async def connect_redis():
    """Connect to Redis."""
    try:
        redis_client.client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


async def close_redis():
    """Close Redis connection."""
    if redis_client.client:
        await redis_client.client.close()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client.client is None:
        raise RuntimeError("Redis not connected")
    return redis_client.client


# Cache utilities
async def cache_set(key: str, value: any, expire: int = 3600):
    """Set cache value with expiration."""
    r = get_redis()
    await r.set(key, json.dumps(value), ex=expire)


async def cache_get(key: str) -> Optional[any]:
    """Get cache value."""
    r = get_redis()
    value = await r.get(key)
    return json.loads(value) if value else None


async def cache_delete(key: str):
    """Delete cache value."""
    r = get_redis()
    await r.delete(key)
