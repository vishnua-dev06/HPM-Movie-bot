"""Movie browsing and catalog keyboards."""

from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.pagination import make_pagination_row


def build_category_years_keyboard(
    category: str,
    years: List[int],
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    """Build keyboard displaying available years for a category."""
    builder = InlineKeyboardBuilder()

    # Place year buttons in rows of 2
    for y in years:
        cb = f"adm_yr:{category}:{y}:1" if is_admin else f"usr_yr:{category}:{y}:1"
        builder.button(text=f"📅 {y}", callback_data=cb)
    builder.adjust(2)

    # Back button
    back_cb = "admin:manage_movies" if is_admin else "user_home"
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data=back_cb))

    return builder.as_markup()


def build_movie_list_keyboard(
    category: str,
    year: int,
    movies: List[Dict[str, Any]],
    page: int,
    total_pages: int,
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    """Build keyboard displaying movies for a selected year with pagination."""
    builder = InlineKeyboardBuilder()

    # List of movie buttons
    for m in movies:
        m_id = str(m["_id"])
        title = m.get("title", "Untitled")
        cb = f"adm_mov:{m_id}" if is_admin else f"mov:{m_id}"
        builder.row(InlineKeyboardButton(text=f"🎬 {title}", callback_data=cb))

    # Pagination controls
    if total_pages > 1:
        prefix = "adm_pg" if is_admin else "usr_pg"
        extra = f"{category}:{year}"
        page_buttons = make_pagination_row(prefix=prefix, page=page, total_pages=total_pages, extra_param=extra)
        builder.row(*page_buttons)

    # Back button
    back_cb = f"adm_cat:{category}" if is_admin else f"cat:{category}"
    builder.row(InlineKeyboardButton(text="◀️ Back to Years", callback_data=back_cb))

    return builder.as_markup()


def build_admin_movie_details_keyboard(
    movie_id: str,
    category: str,
    year: int,
) -> InlineKeyboardMarkup:
    """Build action buttons for an administrator managing a specific movie."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✏️ Edit Title", callback_data=f"adm_edit_name:{movie_id}"),
        InlineKeyboardButton(text="📅 Change Year", callback_data=f"adm_edit_year:{movie_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Change Category", callback_data=f"adm_edit_cat:{movie_id}"),
        InlineKeyboardButton(text="➕ Add Media Messages", callback_data=f"adm_add_media:{movie_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Delete Movie", callback_data=f"adm_del_mov:{movie_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Movies", callback_data=f"adm_yr:{category}:{year}:1"),
    )

    return builder.as_markup()
