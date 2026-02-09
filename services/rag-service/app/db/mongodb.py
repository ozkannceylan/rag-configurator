"""MongoDB connection management."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.settings import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        logger.info(f"Connecting to MongoDB at {settings.mongodb_uri}...")

        self.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=50,
            minPoolSize=10,
        )
        self.database = self.client[settings.mongodb_database]

        # Test connection
        await self.client.admin.command("ping")
        logger.info(f"Connected to MongoDB database: {settings.mongodb_database}")

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return mongodb.get_database()
