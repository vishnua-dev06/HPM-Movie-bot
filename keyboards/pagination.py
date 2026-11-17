"""Pagination keyboard helper."""

from typing import List
from aiogram.types import InlineKeyboardButton


def make_pagination_row(
    prefix: str,
    page: int,
    total_pages: int,
    extra_param: str = "",
) -> List[InlineKeyboardButton]:
    """Create pagination buttons: [Prev] [Page X/Y] [Next]."""
    buttons = []
    suffix = f":{extra_param}" if extra_param else ""

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️ Prev",
                callback_data=f"{prefix}:{page - 1}{suffix}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"📄 {page}/{max(1, total_pages)}",
            callback_data="noop",
        )
    )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="Next ▶️",
                callback_data=f"{prefix}:{page + 1}{suffix}",
            )
        )

    return buttons
