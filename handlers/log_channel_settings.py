"""User Log Channel configuration handlers in Admin Panel."""

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.log_channel import LogChannelRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_log_channel_settings_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from services.log_channel_service import LogChannelService
from utils.logger import logger
from utils.validators import validate_chat_id

router = Router(name="log_channel_settings_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class LogChannelFSM(StatesGroup):
    waiting_for_channel_id = State()


# 1. Log Channel Settings Overview
@router.callback_query(F.data == "admin:log_channel")
async def handle_log_channel_overview(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display User Log Channel settings and status."""
    if state is not None:
        await state.clear()

    config = await LogChannelRepository.get_config()
    channel_id = config.get("channel_id", 0)
    is_enabled = config.get("is_enabled", False)
    log_activities = config.get("log_activities", False)

    status_str = "🟢 Active (Sending registration logs)" if (is_enabled and channel_id) else "🔴 Disabled / Not Configured"
    channel_id_str = f"<code>{channel_id}</code>" if channel_id else "<i>Not Configured</i>"
    activity_str = "🔔 Enabled (Detailed logs)" if log_activities else "🔕 Disabled (Registration only)"

    text = (
        "📡 <b>User Log Channel Configuration</b>\n\n"
        "The bot automatically posts a clean notification whenever a new user starts the bot for the first time.\n\n"
        f"• <b>Status:</b> {status_str}\n"
        f"• <b>Log Channel ID:</b> {channel_id_str}\n"
        f"• <b>Detailed Activity Logs:</b> {activity_str}\n\n"
        "<i>Requirements: The bot must be added as an Administrator in your private Log Channel with post permissions.</i>"
    )
    keyboard = build_log_channel_settings_keyboard(config=config)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 2. Set / Update Log Channel ID
@router.callback_query(F.data == "adm_logch_set_id")
async def handle_set_log_channel_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt administrator for new Log Channel ID."""
    await state.set_state(LogChannelFSM.waiting_for_channel_id)

    text = (
        "✏️ <b>Configure User Log Channel ID</b>\n\n"
        "Please send the numeric Telegram Channel ID for your Log Channel.\n"
        "(Channel IDs typically begin with <code>-100</code>, e.g. <code>-1001987654321</code>)\n\n"
        "<i>Make sure your bot is an Administrator in this channel first!</i>"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:log_channel")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(LogChannelFSM.waiting_for_channel_id, F.text)
async def handle_log_channel_id_input(message: types.Message, state: FSMContext) -> None:
    """Validate and save new Log Channel ID."""
    is_valid, channel_id, err = validate_chat_id(message.text or "")
    if not is_valid or channel_id is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid numeric channel ID:")
        return

    await LogChannelRepository.set_channel_id(channel_id=channel_id)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Log Settings", callback_data="admin:log_channel"))

    await message.answer(
        f"✅ <b>Log Channel ID Configured!</b>\n\n"
        f"Channel ID has been updated to <code>{channel_id}</code>.\n"
        "Use 'Test Connection' in the menu to verify posting permissions.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 3. Test Connection
@router.callback_query(F.data == "adm_logch_test")
async def handle_test_log_channel(callback: types.CallbackQuery, bot: Bot) -> None:
    """Send test verification message to configured Log Channel."""
    config = await LogChannelRepository.get_config()
    channel_id = config.get("channel_id")

    if not channel_id:
        await callback.answer("⚠️ No Log Channel ID is configured yet! Please configure one first.", show_alert=True)
        return

    success, msg = await LogChannelService.test_log_channel(bot=bot, channel_id=channel_id)
    if success:
        await callback.answer("✅ Verification message successfully sent to your Log Channel!", show_alert=True)
    else:
        await callback.answer(f"❌ Test failed: {msg}\nCheck bot admin permissions in the channel.", show_alert=True)


# 4. Toggle Enable / Disable
@router.callback_query(F.data == "adm_logch_toggle")
async def handle_toggle_log_channel(callback: types.CallbackQuery) -> None:
    """Toggle Log Channel active status."""
    config = await LogChannelRepository.get_config()
    new_state = not config.get("is_enabled", False)

    await LogChannelRepository.toggle_enabled(new_state)
    status_str = "Enabled" if new_state else "Disabled"

    await callback.answer(f"✅ Log Channel is now {status_str}!", show_alert=False)
    await handle_log_channel_overview(callback, None)


# 5. Toggle Detailed Activities
@router.callback_query(F.data == "adm_logch_toggle_activities")
async def handle_toggle_activities(callback: types.CallbackQuery) -> None:
    """Toggle detailed activity logs."""
    config = await LogChannelRepository.get_config()
    new_state = not config.get("log_activities", False)

    await LogChannelRepository.toggle_activities(new_state)
    status_str = "Enabled" if new_state else "Disabled"

    await callback.answer(f"✅ Detailed Activity Logs {status_str}!", show_alert=False)
    await handle_log_channel_overview(callback, None)
