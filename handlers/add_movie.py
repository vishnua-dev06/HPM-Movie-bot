"""Forward-based movie upload workflow for administrator."""

from typing import Any, Dict, List
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.activity_logs import ActivityLogRepository
from database.movie_messages import MovieMessageRepository
from database.movies import MovieRepository
from database.years import YearRepository
from handlers.user_menu import CATEGORY_NAMES
from keyboards.admin import build_admin_cancel_keyboard
from middlewares.admin_auth import IsAdminFilter
from services.media_manager import MediaManager
from utils.helpers import escape_html
from utils.logger import logger
from utils.validators import validate_movie_title, validate_year

router = Router(name="add_movie_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class AddMovieFSM(StatesGroup):
    waiting_for_category = State()
    waiting_for_year = State()
    waiting_for_title = State()
    collecting_media = State()


def build_media_collection_keyboard(count: int) -> InlineKeyboardMarkup:
    """Build Finish / Cancel keyboard for media collection state."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"✅ Finish Upload ({count} files)", callback_data="addmov_finish"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel Upload", callback_data="admin:dashboard"),
    )
    return builder.as_markup()


# Step 1 & 2: Admin clicks "Add Movie"
@router.callback_query(F.data == "admin:add_movie")
async def start_add_movie_flow(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Initiate movie upload workflow by selecting a category."""
    await state.clear()
    await state.set_state(AddMovieFSM.waiting_for_category)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Latest Malayalam Movies", callback_data="addmov_cat:latest"),
    )
    builder.row(
        InlineKeyboardButton(text="🎥 Malayalam Dubbed Movies", callback_data="addmov_cat:dubbed"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="admin:dashboard"),
    )

    text = (
        "🎬 <b>Add New Movie — Step 1 of 4: Select Category</b>\n\n"
        "Please select the movie category:"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# Step 3: Admin selects category
@router.callback_query(AddMovieFSM.waiting_for_category, F.data.startswith("addmov_cat:"))
async def handle_category_chosen(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Store category and prompt for release year."""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddMovieFSM.waiting_for_year)

    # Fetch recent years to offer quick buttons
    all_years = await YearRepository.get_all_years(only_enabled=False)
    recent_years = [y["year"] for y in all_years[:8]]

    builder = InlineKeyboardBuilder()
    for yr in recent_years:
        builder.button(text=str(yr), callback_data=f"addmov_yr:{yr}")
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="admin:dashboard"),
    )

    cat_title = CATEGORY_NAMES.get(category, "Movies")
    text = (
        f"🎬 <b>Category:</b> {cat_title}\n\n"
        "📅 <b>Step 2 of 4: Select or Enter Release Year</b>\n\n"
        "Tap one of the existing years below, or simply <b>send the 4-digit year as a message</b> (e.g. <code>2026</code>):"
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# Step 4: Year chosen via button
@router.callback_query(AddMovieFSM.waiting_for_year, F.data.startswith("addmov_yr:"))
async def handle_year_button(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Record selected year button and prompt for movie title."""
    year = int(callback.data.split(":")[1])
    await _proceed_to_title_step(callback, state, year)


# Step 4: Year entered via text message
@router.message(AddMovieFSM.waiting_for_year, F.text)
async def handle_year_text(message: types.Message, state: FSMContext) -> None:
    """Record manually entered year string and prompt for movie title."""
    is_valid, year, err = validate_year(message.text or "")
    if not is_valid or year is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid 4-digit release year (e.g. 2026):")
        return

    await _proceed_to_title_step(message, state, year)


async def _proceed_to_title_step(event: types.Message | types.CallbackQuery, state: FSMContext, year: int) -> None:
    """Transition state to movie title input."""
    await state.update_data(year=year)
    await state.set_state(AddMovieFSM.waiting_for_title)

    data = await state.get_data()
    cat_title = CATEGORY_NAMES.get(data.get("category", ""), "Movies")

    text = (
        f"🎬 <b>Category:</b> {cat_title}\n"
        f"📅 <b>Year:</b> {year}\n\n"
        "✏️ <b>Step 3 of 4: Enter Movie Name</b>\n\n"
        "Please type and send the official movie name:"
    )
    cancel_kb = build_admin_cancel_keyboard()

    if isinstance(event, types.CallbackQuery):
        if event.message:
            await event.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=cancel_kb, parse_mode="HTML")


# Step 5: Admin enters movie title
@router.message(AddMovieFSM.waiting_for_title, F.text)
async def handle_title_input(message: types.Message, state: FSMContext) -> None:
    """Record title and transition to forward-based media collection."""
    is_valid, clean_title, err = validate_movie_title(message.text or "")
    if not is_valid or not clean_title:
        await message.reply(f"⚠️ {err}\nPlease send a valid movie name:")
        return

    await state.update_data(title=clean_title, media_list=[])
    await state.set_state(AddMovieFSM.collecting_media)

    data = await state.get_data()
    cat_title = CATEGORY_NAMES.get(data.get("category", ""), "Movies")
    year = data.get("year")

    text = (
        "📥 <b>Step 4 of 4: Forward-Based Media Upload Active</b>\n\n"
        f"🎬 <b>Movie:</b> {escape_html(clean_title)}\n"
        f"📁 <b>Category:</b> {cat_title}\n"
        f"📅 <b>Year:</b> {year}\n\n"
        "➡️ <b>Now send or forward your media files directly into this chat:</b>\n"
        "• Movie poster (photo or document)\n"
        "• Video files (Video 1, Video 2, etc.)\n"
        "• Authorized Telegram media albums or documents\n\n"
        "📊 <b>Messages Received: 0</b>\n\n"
        "<i>When you have sent all files, click 'Finish Upload' below.</i>"
    )
    keyboard = build_media_collection_keyboard(count=0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# Step 6 & 7: Media collection receiver
@router.message(
    AddMovieFSM.collecting_media,
    F.photo | F.video | F.document | F.audio | F.animation | F.text,
)
async def handle_media_upload_message(message: types.Message, state: FSMContext) -> None:
    """Collect forwarded or sent media messages into the movie buffer."""
    media_info = MediaManager.extract_media_info(message)
    data = await state.get_data()
    media_list: List[Dict[str, Any]] = data.get("media_list", [])

    media_info["order"] = len(media_list)
    media_list.append(media_info)

    await state.update_data(media_list=media_list)
    count = len(media_list)

    media_type_label = media_info.get("media_type", "media").capitalize()
    keyboard = build_media_collection_keyboard(count=count)

    await message.reply(
        f"✅ <b>Received message #{count}</b> ({media_type_label})!\n"
        f"Total collected: <b>{count}</b> file(s).\n\n"
        "Send more files or click <b>Finish Upload</b> below when done.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# Step 8 & 9: Admin clicks "Finish Upload"
@router.callback_query(AddMovieFSM.collecting_media, F.data == "addmov_finish")
async def handle_finish_upload(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save movie metadata and all media references in MongoDB."""
    data = await state.get_data()
    media_list: List[Dict[str, Any]] = data.get("media_list", [])

    if not media_list:
        await callback.answer(
            "⚠️ No media files have been received yet! Please send or forward at least one media file.",
            show_alert=True,
        )
        return

    title = data.get("title", "Untitled")
    category = data.get("category", "latest")
    year = int(data.get("year", 2026))

    # 1. Create Movie document
    movie_id = await MovieRepository.create_movie(
        title=title,
        category=category,
        year=year,
        total_media=len(media_list),
    )

    # 2. Save media message references
    await MovieMessageRepository.add_movie_messages(
        movie_id=movie_id,
        messages=media_list,
    )

    # 3. Ensure year exists in years collection
    await YearRepository.ensure_year_exists(year=year)

    # 4. Audit log
    user_id = callback.from_user.id if callback.from_user else 0
    await ActivityLogRepository.log_activity(
        user_id=user_id,
        action="add_movie",
        details={
            "movie_id": str(movie_id),
            "title": title,
            "category": category,
            "year": year,
            "media_count": len(media_list),
        },
    )

    await state.clear()

    cat_title = CATEGORY_NAMES.get(category, "Movies")
    success_text = (
        "🎉 <b>Movie Added Successfully!</b>\n\n"
        f"🎬 <b>Title:</b> {escape_html(title)}\n"
        f"📁 <b>Category:</b> {cat_title}\n"
        f"📅 <b>Year:</b> {year}\n"
        f"📦 <b>Total Media Files Stored:</b> {len(media_list)}\n"
        f"🆔 <b>Movie ID:</b> <code>{movie_id}</code>\n\n"
        "The movie is now instantly live and available for users in the catalog!"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Add Another Movie", callback_data="admin:add_movie"),
        InlineKeyboardButton(text="◀️ Admin Dashboard", callback_data="admin:dashboard"),
    )

    if callback.message:
        await callback.message.edit_text(success_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer("✅ Movie saved successfully!", show_alert=False)
    logger.info("Movie '%s' (%s) successfully added with %d media items.", title, movie_id, len(media_list))
