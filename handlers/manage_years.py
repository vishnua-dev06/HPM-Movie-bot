"""Year management handlers for administrator."""

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.activity_logs import ActivityLogRepository
from database.years import YearRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_confirm_keyboard,
    build_single_year_actions_keyboard,
    build_years_management_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from utils.logger import logger
from utils.validators import validate_year

router = Router(name="manage_years_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class YearManagementFSM(StatesGroup):
    adding_year = State()
    renaming_year = State()


# 1. Overview of all years
@router.callback_query(F.data == "admin:manage_years")
async def handle_manage_years_overview(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display all release years with administrative management options."""
    if state is not None:
        await state.clear()
    years = await YearRepository.get_all_years(only_enabled=False)

    text = (
        "📅 <b>Release Year Management</b>\n\n"
        "🟢 = Year Enabled | 🔴 = Year Disabled\n\n"
        "Tap a year below to manage its status, rename it, or delete it:"
    )
    keyboard = build_years_management_keyboard(years=years)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 2. Add New Year
@router.callback_query(F.data == "adm_yr_add")
async def handle_add_year_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt administrator to input a new 4-digit year."""
    await state.set_state(YearManagementFSM.adding_year)

    text = (
        "➕ <b>Add Release Year</b>\n\n"
        "Please type and send the 4-digit year to add (e.g. <code>2027</code>):"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_years")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(YearManagementFSM.adding_year, F.text)
async def handle_add_year_input(message: types.Message, state: FSMContext) -> None:
    """Save new release year to database."""
    is_valid, year, err = validate_year(message.text or "")
    if not is_valid or year is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid 4-digit year:")
        return

    added = await YearRepository.add_year(year=year)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Years", callback_data="admin:manage_years"))

    if added:
        await message.answer(
            f"✅ Year <b>{year}</b> has been successfully added!",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"ℹ️ Year <b>{year}</b> already exists in the catalog.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


# 3. Year detail card
@router.callback_query(F.data.startswith("adm_yr_manage:"))
async def handle_single_year_manage(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Show options for an individual year."""
    if state is not None:
        await state.clear()
    year = int(callback.data.split(":")[1])

    movie_count = await YearRepository.count_movies_in_year(year=year)
    all_years = await YearRepository.get_all_years(only_enabled=False)
    year_doc = next((y for y in all_years if y["year"] == year), None)

    is_enabled = year_doc.get("is_enabled", True) if year_doc else True
    status_label = "🟢 Enabled (Visible to users)" if is_enabled else "🔴 Disabled (Hidden from users)"

    text = (
        f"📅 <b>Manage Release Year: {year}</b>\n\n"
        f"<b>Status:</b> {status_label}\n"
        f"<b>Movies in this year:</b> {movie_count}\n\n"
        "Choose an action below:"
    )

    keyboard = build_single_year_actions_keyboard(
        year=year,
        is_enabled=is_enabled,
        movie_count=movie_count,
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 4. Toggle year enabled/disabled
@router.callback_query(F.data.startswith("adm_yr_toggle:"))
async def handle_toggle_year(callback: types.CallbackQuery) -> None:
    """Toggle enabled status of a year."""
    year = int(callback.data.split(":")[1])
    all_years = await YearRepository.get_all_years(only_enabled=False)
    year_doc = next((y for y in all_years if y["year"] == year), None)

    if not year_doc:
        await callback.answer("❌ Year not found.", show_alert=True)
        return

    new_state = not year_doc.get("is_enabled", True)
    await YearRepository.toggle_year_enabled(year=year, is_enabled=new_state)

    status_str = "Enabled" if new_state else "Disabled"
    await callback.answer(f"✅ Year {year} is now {status_str}!", show_alert=False)

    callback.data = f"adm_yr_manage:{year}"
    await handle_single_year_manage(callback, None)  # type: ignore


# 5. Rename year
@router.callback_query(F.data.startswith("adm_yr_rename:"))
async def handle_rename_year_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt administrator for new year value."""
    year = int(callback.data.split(":")[1])
    await state.update_data(old_year=year)
    await state.set_state(YearManagementFSM.renaming_year)

    text = (
        f"✏️ <b>Rename Release Year: {year}</b>\n\n"
        "Send the new 4-digit year. All movies currently filed under this year will be automatically updated:"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_yr_manage:{year}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(YearManagementFSM.renaming_year, F.text)
async def handle_rename_year_input(message: types.Message, state: FSMContext) -> None:
    """Execute year renaming across year collection and movie records."""
    data = await state.get_data()
    old_year = data.get("old_year")

    is_valid, new_year, err = validate_year(message.text or "")
    if not is_valid or new_year is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid 4-digit year:")
        return

    success = await YearRepository.rename_year(old_year=old_year, new_year=new_year)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Years", callback_data="admin:manage_years"))

    if success:
        await message.answer(
            f"✅ Successfully renamed year <b>{old_year}</b> to <b>{new_year}</b>!\n"
            "All associated movies have been updated.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ Could not rename year {old_year}.",
            reply_markup=builder.as_markup(),
        )


# 6. Delete year
@router.callback_query(F.data.startswith("adm_yr_del:"))
async def handle_delete_year_prompt(callback: types.CallbackQuery) -> None:
    """Prompt confirmation before deleting a year."""
    year = int(callback.data.split(":")[1])
    movie_count = await YearRepository.count_movies_in_year(year=year)

    if movie_count == 0:
        # Safe to delete immediately
        await YearRepository.delete_year(year=year, cascade_movies=False)
        await callback.answer(f"✅ Year {year} deleted.", show_alert=True)
        await handle_manage_years_overview(callback, None)  # type: ignore
        return

    # Year contains movies: confirm destructive cascade
    text = (
        f"⚠️ <b>Delete Year {year} Warning</b>\n\n"
        f"Year <b>{year}</b> contains <b>{movie_count}</b> movie(s).\n\n"
        "Deleting this year will also <b>permanently delete all movies and media</b> belonging to this year!\n\n"
        "Are you sure you wish to continue?"
    )
    keyboard = build_confirm_keyboard(
        confirm_callback=f"adm_yr_del_confirm:{year}",
        cancel_callback=f"adm_yr_manage:{year}",
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_yr_del_confirm:"))
async def handle_delete_year_confirmed(callback: types.CallbackQuery) -> None:
    """Cascade delete year and all its movies."""
    year = int(callback.data.split(":")[1])
    await YearRepository.delete_year(year=year, cascade_movies=True)

    await ActivityLogRepository.log_activity(
        user_id=callback.from_user.id if callback.from_user else 0,
        action="delete_year_cascade",
        details={"year": year},
    )

    await callback.answer(f"✅ Year {year} and its movies were permanently deleted.", show_alert=True)
    await handle_manage_years_overview(callback, None)  # type: ignore
