"""MongoDB connection handler."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.settings import settings


class MongoDB:
    """MongoDB connection manager."""

    client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=50,
            minPoolSize=5,
        )
        # Verify connection
        await self.client.admin.command("ping")
        print(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self.client:
            raise RuntimeError("MongoDB client not initialized")
        return self.client[settings.MONGODB_DATABASE]


mongodb = MongoDB()


def get_db() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return mongodb.get_database()
