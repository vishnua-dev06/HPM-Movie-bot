"""Anti-flood rate limiting middleware."""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    """In-memory rate limiter to prevent spam or flood attacks."""

    def __init__(self, limit_seconds: float = 0.5) -> None:
        super().__init__()
        self.limit_seconds = limit_seconds
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        user_id = user.id
        now = time.monotonic()
        last_time = self.user_timestamps.get(user_id, 0.0)

        if now - last_time < self.limit_seconds:
            # Drop silently or answer callback query
            if isinstance(event, CallbackQuery):
                await event.answer("⚠️ Please wait a moment before tapping again.", show_alert=False)
            return None

        self.user_timestamps[user_id] = now

        # Periodic cleanup of timestamps if dictionary grows large
        if len(self.user_timestamps) > 10000:
            threshold = now - 60.0
            self.user_timestamps = {
                uid: ts for uid, ts in self.user_timestamps.items() if ts > threshold
            }

        return await handler(event, data)
