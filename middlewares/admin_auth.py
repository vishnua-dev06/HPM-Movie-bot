"""Admin authorization middleware and filter supporting multiple administrators."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject
from config import settings
from database.admins import AdminRepository
from utils.logger import logger


class AdminAuthMiddleware(BaseMiddleware):
    """Enforces server-side authorization for all admin callbacks and commands across multiple administrators."""

    ADMIN_PREFIXES = ("admin:", "adm_")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = user.id if user else 0

        # Check for callback queries with admin prefixes
        if isinstance(event, CallbackQuery):
            cb_data = event.data or ""
            if any(cb_data.startswith(prefix) for prefix in self.ADMIN_PREFIXES):
                is_authorized = await AdminRepository.is_admin(user_id)
                if not is_authorized:
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
            if text.startswith("/admin"):
                is_authorized = await AdminRepository.is_admin(user_id)
                if not is_authorized:
                    logger.warning(
                        "Unauthorized /admin command attempt blocked: user_id=%s",
                        user_id,
                    )
                    await event.reply("❌ Access denied.")
                    return None

        # Check state: if user is in an admin FSM state, verify admin status
        state = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state and ("Admin" in current_state or "add_movie" in current_state or "Broadcast" in current_state):
                is_authorized = await AdminRepository.is_admin(user_id)
                if not is_authorized:
                    await state.clear()
                    return None

        return await handler(event, data)


class IsAdminFilter(Filter):
    """Filter that matches when the sender is an authorized administrator."""

    async def __call__(self, obj: TelegramObject) -> bool:
        user = getattr(obj, "from_user", None)
        if not user:
            return False
        return await AdminRepository.is_admin(user.id)
