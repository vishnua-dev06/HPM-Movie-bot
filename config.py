"""Configuration settings for Malayalam Movie Bot."""

import os
import re
from typing import List, Optional, Set
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "9211347702:AAEHckjgpkupYUzUn539HvqHuTm-18H4GBU")

    # Legacy Single Admin Telegram User ID
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "7412083181"))

    # Multiple Admin IDs (comma- or space-separated)
    ADMIN_IDS_RAW: str = os.getenv("ADMIN_IDS", "7412083181")

    # MongoDB Atlas Connection URI
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb+srv://vishnugopika177_db_user:J2SzyPFbnr7clkpV@cluster0.mpe44et.mongodb.net/?appName=Cluster0")

    # MongoDB Database Name
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "Sheru_Bhai_moviebot")

    # Fixed Sub 1 (Main Movie Channel)
    SUB1_CHANNEL_ID: int = int(os.getenv("SUB1_CHANNEL_ID", "-1001953506128"))
    SUB1_INVITE_URL: str = os.getenv("SUB1_INVITE_URL", "https://t.me/WMchannelS")

    # User Log Channel ID (Optional, starts with -100 for private channels/supergroups)
    LOG_CHANNEL_ID: int = int(os.getenv("LOG_CHANNEL_ID", "-1003763910569"))
    LOG_USER_ACTIVITIES: bool = os.getenv("LOG_USER_ACTIVITIES", "false").lower() in ("true", "1", "yes")

    # Advanced Broadcast Engine Settings
    BROADCAST_CONCURRENCY: int = int(os.getenv("BROADCAST_CONCURRENCY", "5"))
    BROADCAST_BATCH_SIZE: int = int(os.getenv("BROADCAST_BATCH_SIZE", "500"))
    BROADCAST_DELAY_SECONDS: float = float(os.getenv("BROADCAST_DELAY_SECONDS", "0.05"))

    # Optional Port for Railway / Cloud Health Checks
    PORT: int = int(os.getenv("PORT", "0"))

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

    def get_initial_admin_ids(self) -> List[int]:
        """Parse all configured admin IDs from ADMIN_IDS and ADMIN_ID."""
        admin_set: Set[int] = set()

        if self.ADMIN_ID and self.ADMIN_ID != 0:
            admin_set.add(self.ADMIN_ID)

        if self.ADMIN_IDS_RAW:
            # Match all integers in comma- or space-separated list
            raw_ids = re.split(r"[,;\s]+", self.ADMIN_IDS_RAW.strip())
            for item in raw_ids:
                if item.strip():
                    try:
                        admin_set.add(int(item.strip()))
                    except ValueError:
                        pass

        # Return sorted list preserving order if possible
        result = list(admin_set)
        if self.ADMIN_ID in result:
            result.remove(self.ADMIN_ID)
            result.insert(0, self.ADMIN_ID)
        return result

    @property
    def primary_admin_id(self) -> int:
        """Return the primary owner admin ID."""
        admins = self.get_initial_admin_ids()
        return admins[0] if admins else 0

    def validate(self) -> None:
        """Validate critical environment variables."""
        errors = []
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required.")
        if not self.get_initial_admin_ids():
            errors.append("ADMIN_IDS or ADMIN_ID is required and must contain at least one valid numeric ID.")
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
