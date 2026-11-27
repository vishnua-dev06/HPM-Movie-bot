"""Administrator dashboard and main management handlers."""

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import settings
from database.admins import AdminRepository
from database.log_channel import LogChannelRepository
from keyboards.admin import build_admin_dashboard_keyboard
from middlewares.admin_auth import IsAdminFilter
from utils.helpers import escape_html
from utils.logger import logger

router = Router(name="admin_dashboard_router")
# Apply admin filter to all routes in this router
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(Command("admin"))
async def handle_admin_command(message: types.Message, state: FSMContext) -> None:
    """Handle /admin command to open the Administrator Dashboard."""
    await state.clear()
    text = (
        "👑 <b>Administrator Control Panel</b>\n\n"
        "Welcome to the master control center. Choose an action from the dashboard below to manage movies, "
        "configure force subscription channels, broadcast announcements, manage administrators, or customize settings."
    )
    keyboard = build_admin_dashboard_keyboard()
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:dashboard")
async def handle_admin_dashboard_callback(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Return to the Administrator Dashboard."""
    if state is not None:
        await state.clear()
    text = (
        "👑 <b>Administrator Control Panel</b>\n\n"
        "Welcome to the master control center. Choose an action from the dashboard below to manage movies, "
        "configure force subscription channels, broadcast announcements, manage administrators, or customize settings."
    )
    keyboard = build_admin_dashboard_keyboard()

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "admin:bot_settings")
async def handle_bot_settings(callback: types.CallbackQuery) -> None:
    """Display current bot configuration and system environment information."""
    total_admins = await AdminRepository.count_admins()
    log_config = await LogChannelRepository.get_config()
    log_ch_id = log_config.get("channel_id") or "Not Configured"
    log_status = "🟢 Active" if (log_config.get("is_enabled") and log_config.get("channel_id")) else "🔴 Disabled"

    text = (
        "🔧 <b>Bot Settings & Environment Information</b>\n\n"
        f"• <b>Primary Owner ID:</b> <code>{settings.primary_admin_id}</code>\n"
        f"• <b>Total Authorized Admins:</b> <b>{total_admins}</b>\n"
        f"• <b>User Log Channel:</b> <code>{log_ch_id}</code> ({log_status})\n"
        f"• <b>Database Name:</b> <code>{settings.DATABASE_NAME}</code>\n"
        f"• <b>Sub 1 Channel ID (Fixed):</b> <code>{settings.SUB1_CHANNEL_ID}</code>\n"
        f"• <b>Sub 1 Invite Link:</b> {escape_html(settings.SUB1_INVITE_URL)}\n"
        f"• <b>Broadcast Concurrency:</b> <code>{settings.BROADCAST_CONCURRENCY}</code> workers\n"
        f"• <b>Broadcast Batch Size:</b> <code>{settings.BROADCAST_BATCH_SIZE}</code> users/chunk\n\n"
        "ℹ️ <i>Sub 2, Admins, and Log Channels are dynamically managed via the Admin Dashboard. "
        "Sub 1 is fixed in environment variables for security.</i>"
    )
    keyboard = build_admin_dashboard_keyboard()

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
