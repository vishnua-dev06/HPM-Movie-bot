"""Configuration settings for Malayalam Movie Bot."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Single Administrator Telegram User ID
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

    # MongoDB Atlas Connection URI
    MONGO_URI: str = os.getenv("MONGO_URI", "")

    # MongoDB Database Name
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "malayalam_movie_bot")

    # Fixed Sub 1 (Main Movie Channel)
    SUB1_CHANNEL_ID: int = int(os.getenv("SUB1_CHANNEL_ID", "0"))
    SUB1_INVITE_URL: str = os.getenv("SUB1_INVITE_URL", "")

    # Broadcast Rate Limiting
    BROADCAST_DELAY_SECONDS: float = float(os.getenv("BROADCAST_DELAY_SECONDS", "0.05"))
    BROADCAST_BATCH_SIZE: int = int(os.getenv("BROADCAST_BATCH_SIZE", "20"))

    # Pagination limits
    MOVIES_PER_PAGE: int = 10
    USERS_PER_PAGE: int = 10

    # Default Main Menu Button Configuration
    DEFAULT_BUTTONS = [
        {
            "button_key": "latest_movies",
            "title": "🎬 Latest Malayalam Movies",
            "url": None,
            "is_enabled": True,
            "order": 1,
            "is_external": False,
        },
        {
            "button_key": "dubbed_movies",
            "title": "🎥 Malayalam Dubbed Movies",
            "url": None,
            "is_enabled": True,
            "order": 2,
            "is_external": False,
        },
        {
            "button_key": "search_group",
            "title": "🔎 Movie Search Group",
            "url": "https://t.me/telegram",
            "is_enabled": True,
            "order": 3,
            "is_external": True,
        },
        {
            "button_key": "main_channel",
            "title": "📢 Main Movie Channel",
            "url": "https://t.me/telegram",
            "is_enabled": True,
            "order": 4,
            "is_external": True,
        },
    ]

    def validate(self) -> None:
        """Validate critical environment variables."""
        errors = []
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required.")
        if not self.ADMIN_ID:
            errors.append("ADMIN_ID is required and must be a valid integer.")
        if not self.MONGO_URI:
            errors.append("MONGO_URI is required.")
        if not self.SUB1_CHANNEL_ID:
            errors.append("SUB1_CHANNEL_ID is required.")
        if not self.SUB1_INVITE_URL:
            errors.append("SUB1_INVITE_URL is required.")

        if errors:
            raise ValueError(
                "Configuration errors found:\n" + "\n".join(f"- {e}" for e in errors)
            )


settings = Settings()
