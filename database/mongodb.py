"""MongoDB connection manager and index initializer."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings
from utils.logger import logger


class Database:
    """Singleton MongoDB client and database manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize MongoDB connection, indexes, and initial admin seeding."""
        if cls.client is not None:
            return

        logger.info("Connecting to MongoDB Atlas...")
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=5000,
            )
            # Verify connection with ping
            await cls.client.admin.command("ping")
            cls.db = cls.client[settings.DATABASE_NAME]
            logger.info("MongoDB connected successfully to database: %s", settings.DATABASE_NAME)

            await cls._create_indexes()
            await cls._seed_default_menu_settings()
            await cls._bootstrap_initial_admins()
        except Exception as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            raise

    @classmethod
    async def close(cls) -> None:
        """Close MongoDB connection gracefully."""
        if cls.client is not None:
            logger.info("Closing MongoDB connection...")
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed.")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Return the active database instance."""
        if cls.db is None:
            raise RuntimeError("Database is not connected. Call Database.connect() first.")
        return cls.db

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create required unique and performance indexes."""
        db = cls.get_db()
        logger.info("Ensuring MongoDB collection indexes...")

        # 1. users: unique index on user_id, indexes for query performance
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("joined_at")
        await db.users.create_index("first_started_at")
        await db.users.create_index("status")
        await db.users.create_index("is_blocked")

        # 2. movies: indexes for catalog browsing
        await db.movies.create_index([("category", 1), ("year", -1)])
        await db.movies.create_index("created_at")

        # 3. movie_messages: index by movie_id and order
        await db.movie_messages.create_index([("movie_id", 1), ("order", 1)])

        # 4. years: unique index on year
        await db.years.create_index("year", unique=True)
        await db.years.create_index("order")

        # 5. menu_settings: unique index on button_key
        await db.menu_settings.create_index("button_key", unique=True)
        await db.menu_settings.create_index("order")

        # 6. subscriptions: unique index on slot ("sub2")
        await db.subscriptions.create_index("slot", unique=True)

        # 7. join_requests: compound unique index on user_id + channel_id
        await db.join_requests.create_index(
            [("user_id", 1), ("channel_id", 1)],
            unique=True,
        )

        # 8. broadcasts: index on started_at, status
        await db.broadcasts.create_index("created_at")
        await db.broadcasts.create_index("status")

        # 9. broadcast_recipients: compound unique index and status query index
        await db.broadcast_recipients.create_index(
            [("broadcast_id", 1), ("user_id", 1)],
            unique=True,
        )
        await db.broadcast_recipients.create_index(
            [("broadcast_id", 1), ("status", 1)],
        )

        # 10. admins: unique index on admin_id
        await db.admins.create_index("admin_id", unique=True)

        # 11. user_activity: index on timestamp and user_id
        await db.user_activity.create_index([("user_id", 1), ("timestamp", -1)])
        await db.user_activity.create_index("timestamp")

        # 12. log_channel_settings: unique index on key
        await db.log_channel_settings.create_index("key", unique=True)

        # 13. activity_logs: index on created_at and user_id
        await db.activity_logs.create_index("created_at")
        await db.activity_logs.create_index("user_id")

        logger.info("MongoDB indexes verified successfully.")

    @classmethod
    async def _seed_default_menu_settings(cls) -> None:
        """Seed default menu button settings if not present."""
        db = cls.get_db()
        count = await db.menu_settings.count_documents({})
        if count == 0:
            logger.info("Seeding default menu settings...")
            for btn in settings.DEFAULT_BUTTONS:
                await db.menu_settings.update_one(
                    {"button_key": btn["button_key"]},
                    {"$setOnInsert": btn},
                    upsert=True,
                )
            logger.info("Default menu settings seeded.")

    @classmethod
    async def _bootstrap_initial_admins(cls) -> None:
        """Bootstrap configured environment administrators into MongoDB."""
        from database.admins import AdminRepository
        initial_ids = settings.get_initial_admin_ids()
        if initial_ids:
            await AdminRepository.bootstrap_admins(initial_ids)
