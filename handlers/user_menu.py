"""User menu and category routing handlers."""

from aiogram import F, Router, types
from database.years import YearRepository
from keyboards.movies import build_category_years_keyboard
from utils.logger import logger

router = Router(name="user_menu_router")

CATEGORY_NAMES = {
    "latest": "Latest Malayalam Movies",
    "dubbed": "Malayalam Dubbed Movies",
}


@router.callback_query(F.data.startswith("cat:"))
async def handle_category_selection(callback: types.CallbackQuery) -> None:
    """Handle selection of Latest Malayalam Movies or Malayalam Dubbed Movies."""
    category = callback.data.split(":")[1]
    cat_title = CATEGORY_NAMES.get(category, "Movies")

    # Fetch distinct years that contain available movies for this category
    years = await YearRepository.get_years_with_movies(category=category, only_enabled=True)

    if not years:
        text = (
            f"🎬 <b>{cat_title}</b>\n\n"
            "Currently, there are no movies available in this category.\n"
            "Please check back soon as our catalog is frequently updated!"
        )
        keyboard = build_category_years_keyboard(category=category, years=[], is_admin=False)
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    text = (
        f"🎬 <b>{cat_title}</b>\n\n"
        "Select a release year below to view available movies:"
    )
    keyboard = build_category_years_keyboard(category=category, years=years, is_admin=False)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
