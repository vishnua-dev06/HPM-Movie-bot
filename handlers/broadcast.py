"""Administrator broadcast announcement handlers."""

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.users import UserRepository
from keyboards.admin import build_admin_cancel_keyboard
from middlewares.admin_auth import IsAdminFilter
from services.broadcast_service import BroadcastService
from utils.helpers import format_number
from utils.logger import logger

router = Router(name="broadcast_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


class BroadcastFSM(StatesGroup):
    waiting_for_message = State()
    confirming_broadcast = State()


# 1. Entry point for broadcast
@router.callback_query(F.data == "admin:broadcast")
async def handle_broadcast_entry(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt administrator to send or forward the broadcast message."""
    await state.clear()
    await state.set_state(BroadcastFSM.waiting_for_message)

    total_active = await UserRepository.get_active_users_count()

    text = (
        "📨 <b>Send Global Broadcast Announcement</b>\n\n"
        f"Eligible active recipients: <b>{format_number(total_active)}</b> user(s).\n\n"
        "➡️ <b>Now send or forward the message you want to broadcast:</b>\n"
        "• Plain text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document or audio file\n\n"
        "<i>The exact formatting, media, and caption will be copied to all users.</i>"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:dashboard")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


# 2. Receive message to broadcast and show confirmation
@router.message(
    BroadcastFSM.waiting_for_message,
    F.text | F.photo | F.video | F.document | F.audio | F.animation,
)
async def handle_broadcast_message_received(message: types.Message, state: FSMContext) -> None:
    """Record source message reference and present confirmation dialogue."""
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )
    await state.set_state(BroadcastFSM.confirming_broadcast)

    total_active = await UserRepository.get_active_users_count()

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"🚀 Confirm Broadcast ({format_number(total_active)} Users)",
            callback_data="adm_bcast_confirm",
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel Broadcast", callback_data="admin:dashboard"),
    )

    await message.reply(
        "👁 <b>Broadcast Message Preview Captured!</b>\n\n"
        f"This announcement will be delivered to <b>{format_number(total_active)}</b> registered user(s).\n\n"
        "Are you ready to send this broadcast?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# 3. Confirm and run broadcast
@router.callback_query(BroadcastFSM.confirming_broadcast, F.data == "adm_bcast_confirm")
async def handle_execute_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Execute asynchronous broadcast with rate limiting and output final metrics."""
    data = await state.get_data()
    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")

    if not source_chat_id or not source_message_id:
        await callback.answer("❌ Broadcast message reference lost. Please start again.", show_alert=True)
        await state.clear()
        return

    admin_id = callback.from_user.id if callback.from_user else 0
    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "⏳ <b>Broadcasting in progress...</b>\n\n"
            "Messages are being delivered with anti-flood rate limits. "
            "A final summary report will be sent upon completion.",
            parse_mode="HTML",
        )

    # Run broadcast service
    results = await BroadcastService.run_broadcast(
        bot=bot,
        admin_id=admin_id,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
    )

    total = format_number(results["total_users"])
    success = format_number(results["success_count"])
    failed = format_number(results["failed_count"])
    blocked = format_number(results["blocked_count"])

    report_text = (
        "📊 <b>Broadcast Execution Report</b>\n\n"
        "Broadcast has completed successfully.\n\n"
        f"• <b>Total Target Users:</b> {total}\n"
        f"• <b>✅ Delivered Successfully:</b> {success}\n"
        f"• <b>🚫 Blocked Bots / Inaccessible:</b> {blocked}\n"
        f"• <b>⚠️ Other Failures:</b> {failed}\n\n"
        "<i>Blocked users have been automatically flagged in the database.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Admin Dashboard", callback_data="admin:dashboard"))

    if callback.message:
        await callback.message.answer(report_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer("✅ Broadcast complete!", show_alert=False)
