"""Menu customization settings in MongoDB."""

from typing import Any, Dict, List, Optional
from config import settings
from database.mongodb import Database


class MenuSettingsRepository:
    """Repository managing customizable main menu buttons."""

    @staticmethod
    def _collection():
        return Database.get_db().menu_settings

    @classmethod
    async def get_all_buttons(cls) -> List[Dict[str, Any]]:
        """Retrieve all menu buttons sorted by order."""
        cursor = cls._collection().find({}).sort("order", 1)
        buttons = await cursor.to_list(length=None)
        if not buttons:
            # Re-seed if empty
            await cls.reset_to_defaults()
            buttons = await cls._collection().find({}).sort("order", 1).to_list(length=None)
        return buttons

    @classmethod
    async def get_active_buttons(cls) -> List[Dict[str, Any]]:
        """Retrieve only enabled menu buttons sorted by order."""
        cursor = cls._collection().find({"is_enabled": True}).sort("order", 1)
        return await cursor.to_list(length=None)

    @classmethod
    async def get_button(cls, button_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific menu button by its key."""
        return await cls._collection().find_one({"button_key": button_key})

    @classmethod
    async def update_title(cls, button_key: str, title: str) -> bool:
        """Update button display text."""
        res = await cls._collection().update_one(
            {"button_key": button_key},
            {"$set": {"title": title.strip()}},
        )
        return res.modified_count > 0

    @classmethod
    async def update_url(cls, button_key: str, url: str) -> bool:
        """Update external link for group/channel button."""
        res = await cls._collection().update_one(
            {"button_key": button_key},
            {"$set": {"url": url.strip()}},
        )
        return res.modified_count > 0

    @classmethod
    async def update_order(cls, button_key: str, order: int) -> bool:
        """Update display ordering."""
        res = await cls._collection().update_one(
            {"button_key": button_key},
            {"$set": {"order": order}},
        )
        return res.modified_count > 0

    @classmethod
    async def toggle_enabled(cls, button_key: str, is_enabled: bool) -> bool:
        """Enable or disable button."""
        res = await cls._collection().update_one(
            {"button_key": button_key},
            {"$set": {"is_enabled": is_enabled}},
        )
        return res.modified_count > 0

    @classmethod
    async def reset_to_defaults(cls) -> None:
        """Reset menu settings to default initial configuration."""
        collection = cls._collection()
        await collection.delete_many({})
        for btn in settings.DEFAULT_BUTTONS:
            await collection.insert_one(dict(btn))
