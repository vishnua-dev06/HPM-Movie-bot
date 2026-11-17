"""Admin authorization middleware and filter."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject
from config import settings
from utils.logger import logger


class AdminAuthMiddleware(BaseMiddleware):
    """Enforces server-side authorization for all admin callbacks and commands."""

    ADMIN_PREFIXES = ("admin:", "adm_")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = user.id if user else 0

        # Check for callback queries
        if isinstance(event, CallbackQuery):
            cb_data = event.data or ""
            if any(cb_data.startswith(prefix) for prefix in self.ADMIN_PREFIXES):
                if user_id != settings.ADMIN_ID:
                    logger.warning(
                        "Unauthorized admin callback attempt blocked: user_id=%s data=%s",
                        user_id,
                        cb_data,
                    )
                    await event.answer("❌ Access denied: Administrator only.", show_alert=True)
                    return None

        # Check for admin commands
        elif isinstance(event, Message):
            text = (event.text or "").strip()
            if text.startswith("/admin") and user_id != settings.ADMIN_ID:
                logger.warning(
                    "Unauthorized /admin command attempt blocked: user_id=%s",
                    user_id,
                )
                await event.reply("❌ Access denied.")
                return None

        # Check state: if user is in an admin FSM state, verify admin
        state = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state and ("Admin" in current_state or "add_movie" in current_state):
                if user_id != settings.ADMIN_ID:
                    await state.clear()
                    return None

        return await handler(event, data)


class IsAdminFilter(Filter):
    """Filter that matches only when the sender is the configured administrator."""

    async def __call__(self, obj: TelegramObject) -> bool:
        user = getattr(obj, "from_user", None)
        if not user:
            return False
        return user.id == settings.ADMIN_ID
