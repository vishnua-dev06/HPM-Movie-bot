"""Multiple administrator management handlers."""

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings
from database.admins import AdminRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_admin_management_keyboard,
    build_confirm_keyboard,
    build_remove_admins_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from utils.helpers import escape_html, format_datetime
from utils.logger import logger
from utils.validators import validate_chat_id

router = Router(name="admin_management_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class AdminManagementFSM(StatesGroup):
    waiting_for_admin_id = State()


# 1. Admin Management Overview
@router.callback_query(F.data == "admin:manage_admins")
async def handle_manage_admins_overview(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display Multiple Administrator Management control panel."""
    if state is not None:
        await state.clear()

    total_admins = await AdminRepository.count_admins()
    primary_owner = settings.primary_admin_id

    text = (
        "👥 <b>Multiple Administrator Management</b>\n\n"
        f"• Active Administrators: <b>{total_admins}</b>\n"
        f"• Primary Owner ID: <code>{primary_owner}</code>\n\n"
        "Authorized administrators have full access to the bot's Admin Panel, "
        "including movie uploads, dynamic settings, force subscriptions, and broadcasts.\n\n"
        "Choose an action below:"
    )
    keyboard = build_admin_management_keyboard()

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 2. View All Admins
@router.callback_query(F.data == "adm_view_admins")
async def handle_view_admins(callback: types.CallbackQuery) -> None:
    """List all authorized administrators with their roles and added timestamps."""
    admins = await AdminRepository.get_all_admins()

    admin_lines = []
    for a in admins:
        aid = a.get("admin_id")
        role = a.get("role", "admin").upper()
        added_at = format_datetime(a.get("added_at"))
        added_by = a.get("added_by", 0)
        added_by_str = f"by <code>{added_by}</code>" if added_by else "(System Bootstrap)"

        role_icon = "👑" if role == "OWNER" else "🛡"
        admin_lines.append(f"{role_icon} <code>{aid}</code> [<b>{role}</b>] — Added {added_by_str} on {added_at}")

    list_text = "\n".join(admin_lines) if admin_lines else "No administrators found."

    text = (
        "📋 <b>Authorized Administrators List</b>\n\n"
        f"{list_text}\n\n"
        "<i>All listed administrators possess server-side authorization.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Admin Management", callback_data="admin:manage_admins"))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# 3. Add Administrator Workflow
@router.callback_query(F.data == "adm_add_admin")
async def handle_add_admin_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt administrator to input a new numeric Telegram user ID."""
    await state.set_state(AdminManagementFSM.waiting_for_admin_id)

    text = (
        "➕ <b>Add New Administrator</b>\n\n"
        "Please send the numeric Telegram User ID of the trusted user you wish to grant admin rights to.\n\n"
        "<i>(The user can find their numeric ID by sending /id to @userinfobot)</i>"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_admins")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(AdminManagementFSM.waiting_for_admin_id, F.text)
async def handle_add_admin_input(message: types.Message, state: FSMContext) -> None:
    """Validate numeric ID and save new administrator to MongoDB."""
    is_valid, new_admin_id, err = validate_chat_id(message.text or "")
    if not is_valid or new_admin_id is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid numeric user ID:")
        return

    caller_id = message.from_user.id if message.from_user else 0
    added = await AdminRepository.add_admin(
        admin_id=new_admin_id,
        added_by=caller_id,
        role="admin",
    )
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Admin Management", callback_data="admin:manage_admins"))

    if added:
        await message.answer(
            f"✅ <b>Administrator Added Successfully!</b>\n\n"
            f"User ID <code>{new_admin_id}</code> now has full administrative access to the bot.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"ℹ️ User ID <code>{new_admin_id}</code> is already an active administrator.",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


# 4. Remove Administrator Workflow
@router.callback_query(F.data == "adm_remove_admin_list")
async def handle_remove_admin_list(callback: types.CallbackQuery) -> None:
    """Display list of removable administrators."""
    admins = await AdminRepository.get_all_admins()
    primary_owner = settings.primary_admin_id

    # Filter out primary owner and check total
    removable = [a for a in admins if a.get("admin_id") != primary_owner]

    if not removable:
        await callback.answer(
            "⚠️ No removable secondary administrators found. The primary owner cannot be removed.",
            show_alert=True,
        )
        return

    text = (
        "➖ <b>Remove Administrator</b>\n\n"
        "Select an administrator from the list below to revoke their access:\n"
        "<i>(The primary owner account is protected from removal)</i>"
    )
    keyboard = build_remove_admins_keyboard(admins=admins, protected_owner_id=primary_owner)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_rm_select:"))
async def handle_remove_admin_confirm_prompt(callback: types.CallbackQuery) -> None:
    """Prompt confirmation before revoking admin rights."""
    admin_id = int(callback.data.split(":")[1])

    text = (
        f"⚠️ <b>Confirm Revocation of Admin Rights</b>\n\n"
        f"Are you sure you want to remove administrator <code>{admin_id}</code>?\n\n"
        "They will immediately lose access to the Admin Panel and all administrative tools."
    )
    keyboard = build_confirm_keyboard(
        confirm_callback=f"adm_rm_exec:{admin_id}",
        cancel_callback="admin:manage_admins",
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_rm_exec:"))
async def handle_remove_admin_execute(callback: types.CallbackQuery) -> None:
    """Execute administrator removal."""
    admin_id = int(callback.data.split(":")[1])
    caller_id = callback.from_user.id if callback.from_user else 0

    success, reason = await AdminRepository.remove_admin(
        admin_id=admin_id,
        requested_by=caller_id,
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Admin Management", callback_data="admin:manage_admins"))

    if success:
        text = f"🗑 <b>Administrator Removed</b>\n\nUser ID <code>{admin_id}</code> has been removed from authorized administrators."
        if callback.message:
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer("✅ Administrator removed.", show_alert=False)
    else:
        await callback.answer(f"❌ {reason}", show_alert=True)
