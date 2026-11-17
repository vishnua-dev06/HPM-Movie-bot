"""Year-wise movie catalog browsing for users."""

import math
from aiogram import F, Router, types
from config import settings
from database.movies import MovieRepository
from handlers.user_menu import CATEGORY_NAMES
from keyboards.movies import build_movie_list_keyboard
from utils.logger import logger

router = Router(name="movie_catalog_router")


@router.callback_query(F.data.startswith("usr_yr:"))
async def handle_user_year_selection(callback: types.CallbackQuery) -> None:
    """Handle year selection by user: usr_yr:{category}:{year}:{page}."""
    parts = callback.data.split(":")
    category = parts[1]
    year = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1

    await _render_movie_list(callback, category, year, page)


@router.callback_query(F.data.startswith("usr_pg:"))
async def handle_user_page_navigation(callback: types.CallbackQuery) -> None:
    """Handle movie list pagination: usr_pg:{page}:{category}:{year}."""
    parts = callback.data.split(":")
    page = int(parts[1])
    category = parts[2]
    year = int(parts[3])

    await _render_movie_list(callback, category, year, page)


async def _render_movie_list(
    callback: types.CallbackQuery,
    category: str,
    year: int,
    page: int,
) -> None:
    """Render the paginated list of movies for a category and year."""
    cat_title = CATEGORY_NAMES.get(category, "Movies")
    limit = settings.MOVIES_PER_PAGE
    skip = (page - 1) * limit

    total_movies = await MovieRepository.get_movies_count_by_category_and_year(category, year)
    total_pages = max(1, math.ceil(total_movies / limit))
    page = max(1, min(page, total_pages))

    movies = await MovieRepository.get_movies_by_category_and_year(
        category=category,
        year=year,
        skip=skip,
        limit=limit,
    )

    if not movies:
        text = (
            f"🎬 <b>{cat_title} — {year}</b>\n\n"
            "No movies are currently listed under this year."
        )
    else:
        text = (
            f"🎬 <b>{cat_title} — {year}</b>\n\n"
            f"Found <b>{total_movies}</b> movie(s). Click on any movie below to receive its files:"
        )

    keyboard = build_movie_list_keyboard(
        category=category,
        year=year,
        movies=movies,
        page=page,
        total_pages=total_pages,
        is_admin=False,
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
