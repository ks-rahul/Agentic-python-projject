"""MongoDB connection for chat sessions and messages."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


mongodb = MongoDB()


async def connect_mongodb():
    """Connect to MongoDB."""
    try:
        mongodb.client = AsyncIOMotorClient(settings.MONGODB_URL)
        mongodb.db = mongodb.client[settings.MONGODB_DATABASE]
        
        # Verify connection
        await mongodb.client.admin.command('ping')
        logger.info("Connected to MongoDB", database=settings.MONGODB_DATABASE)
    except Exception as e:
        logger.error("Failed to connect to MongoDB", error=str(e))
        raise


async def close_mongodb():
    """Close MongoDB connection."""
    if mongodb.client:
        mongodb.client.close()
        logger.info("MongoDB connection closed")


def get_mongodb() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    if mongodb.db is None:
        raise RuntimeError("MongoDB not connected")
    return mongodb.db


# Collection getters
def get_sessions_collection():
    return get_mongodb()["sessions"]


def get_messages_collection():
    return get_mongodb()["messages"]
