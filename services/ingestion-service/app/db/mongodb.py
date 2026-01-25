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
        logger.info(f"Connecting to MongoDB at {settings.mongodb_uri}")
        self.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=10,
            minPoolSize=1,
        )
        self.database = self.client[settings.mongodb_database]

        # Verify connection
        try:
            await self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            logger.info("Disconnecting from MongoDB")
            self.client.close()
            self.client = None
            self.database = None

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self.database is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return self.database

    def get_collection(self, name: str):
        """Get a collection by name."""
        return self.get_database()[name]


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return mongodb.get_database()
