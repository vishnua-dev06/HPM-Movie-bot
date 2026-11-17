"""Movie management handlers for administrator."""

import math
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings
from database.activity_logs import ActivityLogRepository
from database.movie_messages import MovieMessageRepository
from database.movies import MovieRepository
from database.years import YearRepository
from handlers.user_menu import CATEGORY_NAMES
from keyboards.admin import build_admin_cancel_keyboard, build_confirm_keyboard
from keyboards.movies import (
    build_admin_movie_details_keyboard,
    build_category_years_keyboard,
    build_movie_list_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from services.media_manager import MediaManager
from utils.helpers import escape_html, format_datetime
from utils.logger import logger
from utils.validators import validate_movie_title, validate_year

router = Router(name="manage_movies_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class ManageMovieFSM(StatesGroup):
    editing_title = State()
    editing_year = State()
    collecting_additional_media = State()


# 1. Manage Movies Category Selection
@router.callback_query(F.data == "admin:manage_movies")
async def handle_manage_movies_entry(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Entry point for managing existing movies."""
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Latest Malayalam Movies", callback_data="adm_cat:latest"),
    )
    builder.row(
        InlineKeyboardButton(text="🎥 Malayalam Dubbed Movies", callback_data="adm_cat:dubbed"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    text = (
        "📂 <b>Manage Movies</b>\n\n"
        "Select the category of movies you wish to manage:"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# 2. Select category -> show years
@router.callback_query(F.data.startswith("adm_cat:"))
async def handle_admin_category_chosen(callback: types.CallbackQuery) -> None:
    """Show available years for the selected category."""
    category = callback.data.split(":")[1]
    cat_title = CATEGORY_NAMES.get(category, "Movies")

    years = await YearRepository.get_years_with_movies(category=category, only_enabled=False)

    if not years:
        text = (
            f"📂 <b>Manage {cat_title}</b>\n\n"
            "No movies found under this category.\n"
            "Click 'Add Movie' from the dashboard to upload movies."
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="admin:manage_movies"))
        if callback.message:
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()
        return

    text = (
        f"📂 <b>Manage {cat_title}</b>\n\n"
        "Select a release year to manage its movies:"
    )
    keyboard = build_category_years_keyboard(category=category, years=years, is_admin=True)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 3. Year selected -> show movies list with pagination
@router.callback_query(F.data.startswith("adm_yr:"))
async def handle_admin_year_selection(callback: types.CallbackQuery) -> None:
    """Display paginated list of movies for admin: adm_yr:{category}:{year}:{page}."""
    parts = callback.data.split(":")
    category = parts[1]
    year = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1

    await _render_admin_movies_list(callback, category, year, page)


# 4. Admin pagination
@router.callback_query(F.data.startswith("adm_pg:"))
async def handle_admin_pagination(callback: types.CallbackQuery) -> None:
    """Handle pagination callback for admin: adm_pg:{page}:{category}:{year}."""
    parts = callback.data.split(":")
    page = int(parts[1])
    category = parts[2]
    year = int(parts[3])

    await _render_admin_movies_list(callback, category, year, page)


async def _render_admin_movies_list(
    callback: types.CallbackQuery,
    category: str,
    year: int,
    page: int,
) -> None:
    """Render movies list for admin."""
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

    text = (
        f"📂 <b>Manage {cat_title} — {year}</b>\n\n"
        f"Total: <b>{total_movies}</b> movie(s).\n"
        "Select a movie below to edit details, add media, or delete:"
    )

    keyboard = build_movie_list_keyboard(
        category=category,
        year=year,
        movies=movies,
        page=page,
        total_pages=total_pages,
        is_admin=True,
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 5. Movie details view
@router.callback_query(F.data.startswith("adm_mov:"))
async def handle_admin_movie_view(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display detailed management card for a movie."""
    if state is not None:
        await state.clear()
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)

    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    cat_title = CATEGORY_NAMES.get(movie.get("category", ""), "Movies")
    title = escape_html(movie.get("title", "Untitled"))
    year = movie.get("year", "N/A")
    total_media = movie.get("total_media", 0)
    created_at = format_datetime(movie.get("created_at"))

    text = (
        f"🎬 <b>Movie Management Card</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Category:</b> {cat_title}\n"
        f"<b>Release Year:</b> {year}\n"
        f"<b>Stored Media Messages:</b> {total_media}\n"
        f"<b>Created Date:</b> {created_at}\n"
        f"<b>Database ID:</b> <code>{movie_id}</code>\n\n"
        "Choose an action below to update this movie:"
    )

    keyboard = build_admin_movie_details_keyboard(
        movie_id=movie_id,
        category=movie.get("category", "latest"),
        year=movie.get("year", 2026),
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 6. Edit Movie Title
@router.callback_query(F.data.startswith("adm_edit_name:"))
async def handle_edit_title_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start editing movie title."""
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    await state.update_data(movie_id=movie_id)
    await state.set_state(ManageMovieFSM.editing_title)

    text = (
        f"✏️ <b>Edit Movie Title</b>\n\n"
        f"Current Title: <b>{escape_html(movie.get('title'))}</b>\n\n"
        "Please send the new title as a message:"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_mov:{movie_id}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(ManageMovieFSM.editing_title, F.text)
async def handle_edit_title_input(message: types.Message, state: FSMContext) -> None:
    """Save updated movie title."""
    data = await state.get_data()
    movie_id = data.get("movie_id")
    is_valid, clean_title, err = validate_movie_title(message.text or "")

    if not is_valid or not clean_title:
        await message.reply(f"⚠️ {err}\nPlease enter a valid movie title:")
        return

    await MovieRepository.update_movie_title(movie_id=movie_id, title=clean_title)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Return to Movie", callback_data=f"adm_mov:{movie_id}"))

    await message.answer(
        f"✅ Movie title updated successfully to: <b>{escape_html(clean_title)}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 7. Change Movie Year
@router.callback_query(F.data.startswith("adm_edit_year:"))
async def handle_edit_year_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start changing movie year."""
    movie_id = callback.data.split(":")[1]
    await state.update_data(movie_id=movie_id)
    await state.set_state(ManageMovieFSM.editing_year)

    text = "📅 <b>Change Release Year</b>\n\nPlease send the new 4-digit year (e.g. 2026):"
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_mov:{movie_id}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(ManageMovieFSM.editing_year, F.text)
async def handle_edit_year_input(message: types.Message, state: FSMContext) -> None:
    """Save updated movie year."""
    data = await state.get_data()
    movie_id = data.get("movie_id")
    is_valid, year, err = validate_year(message.text or "")

    if not is_valid or year is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid 4-digit year:")
        return

    await MovieRepository.update_movie_year(movie_id=movie_id, year=year)
    await YearRepository.ensure_year_exists(year=year)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Return to Movie", callback_data=f"adm_mov:{movie_id}"))

    await message.answer(
        f"✅ Release year updated successfully to: <b>{year}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 8. Change Category
@router.callback_query(F.data.startswith("adm_edit_cat:"))
async def handle_change_category(callback: types.CallbackQuery) -> None:
    """Toggle or change category for movie."""
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    current_cat = movie.get("category", "latest")
    new_cat = "dubbed" if current_cat == "latest" else "latest"

    await MovieRepository.update_movie_category(movie_id=movie_id, category=new_cat)
    new_cat_title = CATEGORY_NAMES.get(new_cat, "Movies")

    await callback.answer(f"✅ Category changed to: {new_cat_title}", show_alert=True)
    # Refresh movie view
    await handle_admin_movie_view(callback, None)  # type: ignore


# 9. Add Media Messages to existing movie
@router.callback_query(F.data.startswith("adm_add_media:"))
async def handle_add_media_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start adding more media messages to an existing movie."""
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    await state.update_data(movie_id=movie_id, media_list=[])
    await state.set_state(ManageMovieFSM.collecting_additional_media)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Save Additional Files", callback_data="adm_save_more_media"))
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data=f"adm_mov:{movie_id}"))

    text = (
        f"➕ <b>Add Media Messages to:</b> {escape_html(movie.get('title'))}\n\n"
        "Send or forward any additional videos, posters, or files into this chat.\n"
        "Click <b>Save Additional Files</b> when finished."
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.message(
    ManageMovieFSM.collecting_additional_media,
    F.photo | F.video | F.document | F.audio | F.animation | F.text,
)
async def handle_more_media_message(message: types.Message, state: FSMContext) -> None:
    """Collect additional media message into buffer."""
    media_info = MediaManager.extract_media_info(message)
    data = await state.get_data()
    media_list = data.get("media_list", [])

    media_info["order"] = len(media_list)
    media_list.append(media_info)
    await state.update_data(media_list=media_list)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Save Additional Files ({len(media_list)})",
            callback_data="adm_save_more_media",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"adm_mov:{data.get('movie_id')}",
        )
    )

    await message.reply(
        f"✅ Received file #{len(media_list)}! Send more or click Save below.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(ManageMovieFSM.collecting_additional_media, F.data == "adm_save_more_media")
async def handle_save_more_media(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Commit additional media messages to MongoDB."""
    data = await state.get_data()
    movie_id = data.get("movie_id")
    media_list = data.get("media_list", [])

    if not media_list:
        await callback.answer("⚠️ No new media files received.", show_alert=True)
        return

    await MovieMessageRepository.add_movie_messages(movie_id=movie_id, messages=media_list)
    await state.clear()

    await callback.answer(f"✅ Added {len(media_list)} new file(s) to movie!", show_alert=True)
    # Refresh movie view
    callback.data = f"adm_mov:{movie_id}"
    await handle_admin_movie_view(callback, state)


# 10. Delete Movie Flow
@router.callback_query(F.data.startswith("adm_del_mov:"))
async def handle_delete_movie_prompt(callback: types.CallbackQuery) -> None:
    """Prompt confirmation before deleting movie."""
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    title = escape_html(movie.get("title"))
    text = (
        f"⚠️ <b>Confirm Movie Deletion</b>\n\n"
        f"Are you sure you want to permanently delete:\n"
        f"🎬 <b>{title}</b>\n\n"
        "This will permanently delete the movie and all its stored media references. "
        "This action cannot be undone."
    )
    keyboard = build_confirm_keyboard(
        confirm_callback=f"adm_del_confirm:{movie_id}",
        cancel_callback=f"adm_mov:{movie_id}",
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_confirm:"))
async def handle_delete_movie_confirmed(callback: types.CallbackQuery) -> None:
    """Execute permanent deletion of movie."""
    movie_id = callback.data.split(":")[1]
    movie = await MovieRepository.get_movie_by_id(movie_id)

    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return

    title = movie.get("title")
    category = movie.get("category", "latest")
    year = movie.get("year", 2026)

    # Perform cascading delete
    await MovieRepository.delete_movie(movie_id=movie_id)

    # Log audit
    user_id = callback.from_user.id if callback.from_user else 0
    await ActivityLogRepository.log_activity(
        user_id=user_id,
        action="delete_movie",
        details={"movie_id": str(movie_id), "title": title},
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Back to Movies",
            callback_data=f"adm_yr:{category}:{year}:1",
        )
    )

    text = f"🗑 <b>Movie Deleted</b>\n\n<b>{escape_html(title)}</b> has been permanently deleted from the database."
    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer("✅ Movie deleted.", show_alert=False)
    logger.info("Movie %s ('%s') was deleted by admin %d", movie_id, title, user_id)
