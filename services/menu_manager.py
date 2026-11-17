"""Menu business logic and retrieval."""

from typing import Any, Dict, List
from database.settings import MenuSettingsRepository


class MenuManager:
    """Manages menu generation and settings retrieval."""

    @classmethod
    async def get_active_buttons(cls) -> List[Dict[str, Any]]:
        """Fetch active buttons sorted by display order."""
        return await MenuSettingsRepository.get_active_buttons()

    @classmethod
    async def get_all_buttons(cls) -> List[Dict[str, Any]]:
        """Fetch all menu buttons (active and disabled) sorted by order."""
        return await MenuSettingsRepository.get_all_buttons()
