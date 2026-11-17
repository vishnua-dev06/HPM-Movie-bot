"""Start command and main menu handler."""

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from config import settings
from database.users import UserRepository
from keyboards.user import build_user_main_menu
from services.menu_manager import MenuManager
from utils.helpers import escape_html
from utils.logger import logger

router = Router(name="start_router")


@router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext) -> None:
    """Handle /start command, register user, and display the main menu."""
    await state.clear()
    user = message.from_user
    if not user:
        return

    is_admin = (user.id == settings.ADMIN_ID)

    # Register or update user in database
    await UserRepository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_admin=is_admin,
    )

    # Fetch dynamic menu buttons
    buttons = await MenuManager.get_active_buttons()
    keyboard = build_user_main_menu(buttons=buttons, is_admin=is_admin)

    user_name = escape_html(user.first_name)
    welcome_text = (
        f"👋 <b>Welcome to Malayalam Movie Bot, {user_name}!</b>\n\n"
        "🎬 Explore our collection of the latest Malayalam movies and high-quality dubbed releases.\n\n"
        "Please select a category below to browse movies by release year:"
    )

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    logger.info("User %d started the bot (is_admin=%s)", user.id, is_admin)


@router.callback_query(lambda c: c.data == "user_home")
async def handle_user_home(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle navigation back to user main menu."""
    await state.clear()
    user = callback.from_user
    is_admin = (user.id == settings.ADMIN_ID) if user else False

    buttons = await MenuManager.get_active_buttons()
    keyboard = build_user_main_menu(buttons=buttons, is_admin=is_admin)

    user_name = escape_html(user.first_name if user else "User")
    welcome_text = (
        f"👋 <b>Welcome to Malayalam Movie Bot, {user_name}!</b>\n\n"
        "🎬 Explore our collection of the latest Malayalam movies and high-quality dubbed releases.\n\n"
        "Please select a category below to browse movies by release year:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await callback.message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
