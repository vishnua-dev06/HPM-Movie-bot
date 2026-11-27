"""Advanced High-Performance Broadcast announcement handlers with multi-message support and live preview."""

from typing import Any, Dict, List
from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.users import UserRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_broadcast_collection_keyboard,
    build_confirm_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from services.broadcast_service import BroadcastService
from utils.helpers import format_number
from utils.logger import logger

router = Router(name="broadcast_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class AdvancedBroadcastFSM(StatesGroup):
    collecting_messages = State()
    confirming_send = State()


# 1. Entry point for Advanced Broadcast
@router.callback_query(F.data == "admin:broadcast")
async def handle_broadcast_entry(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Prompt administrator to initiate message collection for broadcast."""
    if state is not None:
        await state.clear()
    await state.set_state(AdvancedBroadcastFSM.collecting_messages)
    await state.update_data(messages=[])

    total_active = await UserRepository.get_active_users_count()

    text = (
        "📨 <b>Advanced Broadcast System</b>\n\n"
        f"• Eligible Registered Recipients: <b>{format_number(total_active)}</b> user(s)\n"
        f"• Messages Collected: <b>0</b>\n\n"
        "➡️ <b>Send or forward your message(s) to broadcast:</b>\n"
        "• Plain text message\n"
        "• Photos, Videos, or Media Albums\n"
        "• Documents, Audio, Voice notes, Stickers, or Animations\n\n"
        "<i>You can send multiple messages. They will be delivered together in exact order.</i>"
    )
    keyboard = build_broadcast_collection_keyboard(collected_count=0)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 2. Message Collection Receiver
@router.message(
    AdvancedBroadcastFSM.collecting_messages,
    F.text | F.photo | F.video | F.document | F.audio | F.voice | F.animation | F.sticker,
)
async def handle_collect_broadcast_message(message: types.Message, state: FSMContext) -> None:
    """Collect forwarded or sent message into broadcast buffer."""
    msg_info = BroadcastService.extract_message_info(message)
    data = await state.get_data()
    messages_list: List[Dict[str, Any]] = data.get("messages", [])

    messages_list.append(msg_info)
    await state.update_data(messages=messages_list)

    count = len(messages_list)
    media_label = msg_info.get("media_type", "message").capitalize()
    keyboard = build_broadcast_collection_keyboard(collected_count=count)

    await message.reply(
        f"✅ <b>Collected message #{count}</b> ({media_label})!\n"
        f"Total in broadcast buffer: <b>{count}</b> message(s).\n\n"
        "Send more messages, preview the broadcast, or click <b>SEND THIS MESSAGE</b> when ready.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# 3. Add More Messages button
@router.callback_query(AdvancedBroadcastFSM.collecting_messages, F.data == "bcast_add_more")
async def handle_add_more_messages(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Notify administrator that message collection remains active."""
    data = await state.get_data()
    count = len(data.get("messages", []))
    await callback.answer(f"📥 Send or forward additional messages. Current count: {count}", show_alert=True)


# 4. Preview Broadcast Content
@router.callback_query(AdvancedBroadcastFSM.collecting_messages, F.data == "bcast_preview")
async def handle_preview_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Send copies of all collected broadcast messages back to the administrator for review."""
    data = await state.get_data()
    messages_list: List[Dict[str, Any]] = data.get("messages", [])

    if not messages_list:
        await callback.answer("⚠️ No messages collected yet! Send at least one message first.", show_alert=True)
        return

    admin_id = callback.from_user.id if callback.from_user else 0
    await callback.answer("Sending preview...", show_alert=False)

    if callback.message:
        await callback.message.answer(
            f"👁 <b>BROADCAST PREVIEW ({len(messages_list)} message(s)):</b>\n"
            "Below is the exact content that will be delivered to users:\n"
            "────────────────────────",
            parse_mode="HTML",
        )

    # Deliver preview directly to admin
    await BroadcastService.deliver_messages_to_user(
        bot=bot,
        user_id=admin_id,
        messages=messages_list,
    )

    keyboard = build_broadcast_collection_keyboard(collected_count=len(messages_list))
    if callback.message:
        await callback.message.answer(
            "────────────────────────\n"
            "Review complete. Choose an option below:",
            reply_markup=keyboard,
        )


# 5. Prompt Send Confirmation
@router.callback_query(AdvancedBroadcastFSM.collecting_messages, F.data == "bcast_confirm_send")
async def handle_confirm_send_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Confirm dispatch of the broadcast to all registered users."""
    data = await state.get_data()
    messages_list: List[Dict[str, Any]] = data.get("messages", [])

    if not messages_list:
        await callback.answer("⚠️ No messages in broadcast buffer! Send a message first.", show_alert=True)
        return

    total_active = await UserRepository.get_active_users_count()
    await state.set_state(AdvancedBroadcastFSM.confirming_send)

    text = (
        "🚀 <b>CONFIRM BROADCAST DISPATCH</b>\n\n"
        f"• <b>Total Messages:</b> {len(messages_list)}\n"
        f"• <b>Total Target Recipients:</b> {format_number(total_active)} registered users\n"
        f"• <b>Delivery Mode:</b> High-performance controlled async worker with flood protection\n\n"
        "Are you sure you want to begin broadcasting now?"
    )
    keyboard = build_confirm_keyboard(
        confirm_callback="bcast_execute_now",
        cancel_callback="admin:dashboard",
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# 6. Execute Broadcast
@router.callback_query(AdvancedBroadcastFSM.confirming_send, F.data == "bcast_execute_now")
async def handle_execute_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Launch the background broadcast worker and display real-time live progress."""
    data = await state.get_data()
    messages_list: List[Dict[str, Any]] = data.get("messages", [])

    if not messages_list:
        await callback.answer("❌ Message buffer lost. Please start again.", show_alert=True)
        await state.clear()
        return

    admin_id = callback.from_user.id if callback.from_user else 0
    await state.clear()

    total_active = await UserRepository.get_active_users_count()

    status_msg = None
    if callback.message:
        status_msg = await callback.message.edit_text(
            "⏳ <b>INITIALIZING BROADCAST ENGINE...</b>\n\n"
            f"Preparing delivery queue for <b>{format_number(total_active)}</b> users.\n"
            "Progress will update automatically below.",
            parse_mode="HTML",
        )

    # Launch background worker
    broadcast_id = await BroadcastService.start_broadcast(
        bot=bot,
        admin_id=admin_id,
        messages=messages_list,
        status_message=status_msg,
    )

    await callback.answer("🚀 Broadcast started in background!", show_alert=False)
    logger.info("Admin %d launched broadcast #%s", admin_id, broadcast_id)
