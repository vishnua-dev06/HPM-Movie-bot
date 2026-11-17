"""User panel keyboards."""

from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_user_main_menu(
    buttons: List[Dict[str, Any]],
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    """Build the dynamic 4-button user main menu from database settings."""
    builder = InlineKeyboardBuilder()

    # Sort buttons by configured order
    sorted_buttons = sorted(buttons, key=lambda b: b.get("order", 999))

    for btn in sorted_buttons:
        if not btn.get("is_enabled", True):
            continue

        title = btn.get("title", "Button")
        key = btn.get("button_key")
        url = btn.get("url")

        if key == "latest_movies":
            builder.button(text=title, callback_data="cat:latest")
            builder.adjust(1)
        elif key == "dubbed_movies":
            builder.button(text=title, callback_data="cat:dubbed")
            builder.adjust(1)
        elif key in ("search_group", "main_channel") or btn.get("is_external", False):
            if url:
                builder.button(text=title, url=url)
                builder.adjust(1)

    # If the user is the administrator, provide a quick entry to Admin Panel
    if is_admin:
        builder.button(text="⚡ Open Admin Dashboard", callback_data="admin:dashboard")
        builder.adjust(1)

    return builder.as_markup()


def build_force_sub_keyboard(
    sub1_url: str,
    sub2_info: Optional[Dict[str, Any]],
    movie_id: str,
) -> InlineKeyboardMarkup:
    """Build force-subscribe required channels keyboard with TRY AGAIN."""
    builder = InlineKeyboardBuilder()

    # Sub 1 - Main Movie Channel
    builder.row(
        InlineKeyboardButton(
            text="📢 Join Main Movie Channel",
            url=sub1_url,
        )
    )

    # Sub 2 - Additional Channel (if enabled and has URL)
    if sub2_info and sub2_info.get("is_enabled", False) and sub2_info.get("invite_url"):
        builder.row(
            InlineKeyboardButton(
                text="➕ Join Additional Channel",
                url=sub2_info["invite_url"],
            )
        )

    # TRY AGAIN verification button
    builder.row(
        InlineKeyboardButton(
            text="🔄 TRY AGAIN",
            callback_data=f"try_sub:{movie_id}",
        )
    )

    return builder.as_markup()
