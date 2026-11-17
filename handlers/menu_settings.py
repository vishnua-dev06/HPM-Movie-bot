"""Dynamic menu settings customization handlers."""

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.settings import MenuSettingsRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_menu_button_detail_keyboard,
    build_menu_settings_overview_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from utils.helpers import escape_html
from utils.logger import logger
from utils.validators import validate_url

router = Router(name="menu_settings_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class MenuEditFSM(StatesGroup):
    editing_title = State()
    editing_order = State()
    editing_url = State()


# 1. Menu Settings Overview
@router.callback_query(F.data == "admin:menu_settings")
async def handle_menu_settings_overview(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Show overview of all 4 configurable main menu buttons."""
    if state is not None:
        await state.clear()
    buttons = await MenuSettingsRepository.get_all_buttons()

    text = (
        "⚙️ <b>Dynamic Main Menu Customization</b>\n\n"
        "Here you can customize the 4 buttons on the user main menu:\n"
        "• Edit button labels\n"
        "• Change display order (1 to 4)\n"
        "• Enable or disable buttons\n"
        "• Update Telegram group & channel links\n"
        "• Restore default settings\n\n"
        "Tap any button below to customize it:"
    )
    keyboard = build_menu_settings_overview_keyboard(buttons=buttons)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 2. Edit specific button
@router.callback_query(F.data.startswith("adm_menu_edit:"))
async def handle_button_detail_view(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display individual button configuration options."""
    if state is not None:
        await state.clear()
    btn_key = callback.data.split(":")[1]
    button = await MenuSettingsRepository.get_button(btn_key)

    if not button:
        await callback.answer("❌ Button not found.", show_alert=True)
        return

    title = escape_html(button.get("title", "Untitled"))
    order = button.get("order", 0)
    is_enabled = button.get("is_enabled", True)
    status_str = "🟢 Enabled (Visible)" if is_enabled else "🔴 Disabled (Hidden)"
    url_str = escape_html(button.get("url") or "None (Internal Navigation)")

    text = (
        f"⚙️ <b>Configure Button:</b> <code>{btn_key}</code>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Display Order:</b> #{order}\n"
        f"<b>Status:</b> {status_str}\n"
        f"<b>Destination Link:</b> {url_str}\n\n"
        "Choose an attribute to edit:"
    )
    keyboard = build_menu_button_detail_keyboard(button=button)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 3. Toggle button enabled/disabled
@router.callback_query(F.data.startswith("adm_btn_toggle:"))
async def handle_toggle_button(callback: types.CallbackQuery) -> None:
    """Toggle button active status."""
    btn_key = callback.data.split(":")[1]
    button = await MenuSettingsRepository.get_button(btn_key)
    if not button:
        await callback.answer("❌ Button not found.", show_alert=True)
        return

    new_status = not button.get("is_enabled", True)
    await MenuSettingsRepository.toggle_enabled(button_key=btn_key, is_enabled=new_status)

    status_str = "Enabled" if new_status else "Disabled"
    await callback.answer(f"✅ Button is now {status_str}!", show_alert=False)

    callback.data = f"adm_menu_edit:{btn_key}"
    await handle_button_detail_view(callback, None)  # type: ignore


# 4. Edit title
@router.callback_query(F.data.startswith("adm_btn_title:"))
async def handle_edit_title_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt for new button title."""
    btn_key = callback.data.split(":")[1]
    await state.update_data(btn_key=btn_key)
    await state.set_state(MenuEditFSM.editing_title)

    text = (
        f"✏️ <b>Edit Button Title for:</b> <code>{btn_key}</code>\n\n"
        "Please send the new button label as a message (e.g. <code>🎬 Latest Malayalam Movies</code>):"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_menu_edit:{btn_key}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MenuEditFSM.editing_title, F.text)
async def handle_edit_title_input(message: types.Message, state: FSMContext) -> None:
    """Save updated button title."""
    data = await state.get_data()
    btn_key = data.get("btn_key")
    new_title = (message.text or "").strip()

    if not new_title or len(new_title) > 60:
        await message.reply("⚠️ Title must be between 1 and 60 characters. Please send again:")
        return

    await MenuSettingsRepository.update_title(button_key=btn_key, title=new_title)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Button", callback_data=f"adm_menu_edit:{btn_key}"))

    await message.answer(
        f"✅ Button title updated to: <b>{escape_html(new_title)}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 5. Change order
@router.callback_query(F.data.startswith("adm_btn_order:"))
async def handle_edit_order_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt for new button order integer."""
    btn_key = callback.data.split(":")[1]
    await state.update_data(btn_key=btn_key)
    await state.set_state(MenuEditFSM.editing_order)

    text = (
        f"🔢 <b>Change Display Order for:</b> <code>{btn_key}</code>\n\n"
        "Send a number between 1 and 10 to set its display position:"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_menu_edit:{btn_key}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MenuEditFSM.editing_order, F.text)
async def handle_edit_order_input(message: types.Message, state: FSMContext) -> None:
    """Save updated button order."""
    data = await state.get_data()
    btn_key = data.get("btn_key")

    try:
        order = int((message.text or "").strip())
        if order < 1 or order > 20:
            raise ValueError()
    except ValueError:
        await message.reply("⚠️ Please send a valid positive number (e.g. 1, 2, 3, 4):")
        return

    await MenuSettingsRepository.update_order(button_key=btn_key, order=order)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Button", callback_data=f"adm_menu_edit:{btn_key}"))

    await message.answer(
        f"✅ Display order for <code>{btn_key}</code> updated to <b>#{order}</b>!",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 6. Edit URL for external buttons
@router.callback_query(F.data.startswith("adm_btn_url:"))
async def handle_edit_url_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt for new URL for Telegram group/channel button."""
    btn_key = callback.data.split(":")[1]
    await state.update_data(btn_key=btn_key)
    await state.set_state(MenuEditFSM.editing_url)

    text = (
        f"🔗 <b>Update Destination Link for:</b> <code>{btn_key}</code>\n\n"
        "Please send the new Telegram URL (e.g. <code>https://t.me/your_group</code>):"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data=f"adm_menu_edit:{btn_key}")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MenuEditFSM.editing_url, F.text)
async def handle_edit_url_input(message: types.Message, state: FSMContext) -> None:
    """Save updated URL."""
    data = await state.get_data()
    btn_key = data.get("btn_key")
    url_text = (message.text or "").strip()

    is_valid, err = validate_url(url_text)
    if not is_valid:
        await message.reply(f"⚠️ {err}\nPlease send a valid URL starting with https://:")
        return

    await MenuSettingsRepository.update_url(button_key=btn_key, url=url_text)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Button", callback_data=f"adm_menu_edit:{btn_key}"))

    await message.answer(
        f"✅ Destination link updated successfully to:\n{escape_html(url_text)}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 7. Restore defaults
@router.callback_query(F.data == "adm_menu_restore")
async def handle_restore_defaults(callback: types.CallbackQuery) -> None:
    """Restore all menu buttons to factory defaults."""
    await MenuSettingsRepository.reset_to_defaults()
    await callback.answer("✅ Menu settings restored to factory defaults!", show_alert=True)
    await handle_menu_settings_overview(callback, None)  # type: ignore
