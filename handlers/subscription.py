"""Force subscription configuration and chat join request handler."""

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ChatJoinRequest, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings
from database.join_requests import JoinRequestRepository
from database.subscriptions import SubscriptionRepository
from keyboards.admin import (
    build_admin_cancel_keyboard,
    build_sub2_management_keyboard,
)
from middlewares.admin_auth import IsAdminFilter
from utils.helpers import escape_html
from utils.logger import logger
from utils.validators import validate_chat_id, validate_url

router = Router(name="subscription_router")


# FSM for Sub 2 Setup and Edit
class Sub2SetupFSM(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_type = State()
    waiting_for_invite_url = State()
    editing_channel_id = State()
    editing_invite_url = State()


# -------------------------------------------------------------
# 1. Chat Join Request Update Handler (PUBLIC / SYSTEM ROUTE)
# -------------------------------------------------------------
@router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest) -> None:
    """Handle incoming Join Request for private channels and record user ID in MongoDB.

    BUSINESS RULE:
    Receiving and recording the user's valid Join Request satisfies the Sub 2 condition.
    The bot does NOT call approveChatJoinRequest automatically. Users gain access
    without waiting for manual administrator approval.
    """
    user_id = event.from_user.id
    channel_id = event.chat.id

    logger.info("Received ChatJoinRequest: user=%d in channel=%d", user_id, channel_id)

    # Record the request in MongoDB
    await JoinRequestRepository.record_join_request(
        user_id=user_id,
        channel_id=channel_id,
    )


# -------------------------------------------------------------
# 2. Admin Panel: Subscription Management Dashboard
# -------------------------------------------------------------
@router.callback_query(IsAdminFilter(), F.data == "admin:manage_sub")
async def handle_manage_sub_dashboard(callback: types.CallbackQuery, state: FSMContext = None) -> None:
    """Display force subscription dashboard (Sub 1 Fixed & Sub 2 Dynamic)."""
    if state is not None:
        await state.clear()
    sub2 = await SubscriptionRepository.get_sub2()

    # Sub 1 details (Fixed)
    sub1_text = (
        "<b>📌 SUB 1 — Fixed Main Movie Channel (Always Required)</b>\n"
        f"• Status: 🟢 Permanent & Mandatory\n"
        f"• Channel ID: <code>{settings.SUB1_CHANNEL_ID}</code>\n"
        f"• Invite URL: {escape_html(settings.SUB1_INVITE_URL)}\n"
        "<i>(Configured via environment variables; cannot be removed from admin panel)</i>\n"
    )

    # Sub 2 details (Dynamic)
    if sub2:
        is_enabled = sub2.get("is_enabled", False)
        status_label = "🟢 Enabled (Mandatory)" if is_enabled else "🔴 Disabled (Ignored)"
        ch_type = sub2.get("channel_type", "public")
        type_label = "🌐 Public Channel" if ch_type == "public" else "🔒 Private Channel (Join Request)"
        ch_id = sub2.get("channel_id", "Not set")
        invite_url = sub2.get("invite_url", "Not set")

        sub2_text = (
            "\n<b>📌 SUB 2 — Dynamic Additional Channel</b>\n"
            f"• Status: {status_label}\n"
            f"• Mode: {type_label}\n"
            f"• Channel ID: <code>{ch_id}</code>\n"
            f"• Invite Link: {escape_html(invite_url)}\n"
        )
    else:
        sub2_text = (
            "\n<b>📌 SUB 2 — Dynamic Additional Channel</b>\n"
            "• Status: ⚪ Not Configured (Users only need to join Sub 1)\n"
            "<i>Click 'Setup Sub 2 Channel' below to add a second channel.</i>\n"
        )

    text = (
        "📢 <b>Force Subscription Management</b>\n\n"
        f"{sub1_text}\n"
        f"{sub2_text}\n"
        "Configure or toggle Sub 2 below:"
    )

    keyboard = build_sub2_management_keyboard(sub2=sub2)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# -------------------------------------------------------------
# 3. Sub 2 Setup Wizard (FSM)
# -------------------------------------------------------------
@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_setup")
async def start_sub2_setup(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start wizard to configure Sub 2."""
    await state.clear()
    await state.set_state(Sub2SetupFSM.waiting_for_channel_id)

    text = (
        "➕ <b>Setup Sub 2 Channel — Step 1 of 3</b>\n\n"
        "Please send the numeric Telegram Channel ID for Sub 2.\n"
        "(Channel IDs typically begin with <code>-100</code>, e.g. <code>-1001987654321</code>)\n\n"
        "<i>Make sure your bot has been added as an Administrator in this channel first!</i>"
    )
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_sub")

    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(IsAdminFilter(), Sub2SetupFSM.waiting_for_channel_id, F.text)
async def handle_sub2_channel_id_input(message: types.Message, state: FSMContext) -> None:
    """Validate channel ID and prompt for channel type."""
    is_valid, channel_id, err = validate_chat_id(message.text or "")
    if not is_valid or channel_id is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid numeric channel ID:")
        return

    await state.update_data(channel_id=channel_id)
    await state.set_state(Sub2SetupFSM.waiting_for_channel_type)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 Public Channel", callback_data="sub2_type:public"),
        InlineKeyboardButton(text="🔒 Private (Join Request)", callback_data="sub2_type:private_request"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="admin:manage_sub"),
    )

    text = (
        f"📢 <b>Channel ID:</b> <code>{channel_id}</code>\n\n"
        "⚙️ <b>Step 2 of 3: Select Channel Type</b>\n\n"
        "• <b>Public Channel:</b> Bot verifies user membership directly via getChatMember.\n"
        "• <b>Private Channel (Join Request):</b> Bot creates/receives Join Requests and records them in MongoDB without requiring manual approval."
    )
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(IsAdminFilter(), Sub2SetupFSM.waiting_for_channel_type, F.data.startswith("sub2_type:"))
async def handle_sub2_type_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Record channel type and prompt for or generate invite link."""
    ch_type = callback.data.split(":")[1]
    await state.update_data(channel_type=ch_type)
    await state.set_state(Sub2SetupFSM.waiting_for_invite_url)

    data = await state.get_data()
    channel_id = data.get("channel_id")

    # If private request, attempt to generate join request invite link automatically
    suggested_link = None
    if ch_type == "private_request":
        try:
            link_obj = await bot.create_chat_invite_link(
                chat_id=channel_id,
                name="Movie Bot Join Request",
                creates_join_request=True,
            )
            suggested_link = link_obj.invite_link
        except Exception as e:
            logger.warning("Could not auto-generate join request link: %s", e)

    if suggested_link:
        # Prompt admin with auto-generated link option or manual entry
        await state.update_data(invite_url=suggested_link)
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Use Auto-Generated Link", callback_data="sub2_use_auto_link"),
        )
        builder.row(
            InlineKeyboardButton(text="❌ Cancel", callback_data="admin:manage_sub"),
        )
        text = (
            "🔗 <b>Step 3 of 3: Invite Link</b>\n\n"
            f"An invite link with <b>creates_join_request=True</b> was automatically generated:\n"
            f"<code>{suggested_link}</code>\n\n"
            "Click 'Use Auto-Generated Link' below, or send a custom invite link as a message:"
        )
        if callback.message:
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        text = (
            "🔗 <b>Step 3 of 3: Enter Invite Link</b>\n\n"
            "Please send the Telegram invite link (e.g. <code>https://t.me/+AbCdEfGhIjK</code> or <code>https://t.me/your_channel</code>):"
        )
        cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_sub")
        if callback.message:
            await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")

    await callback.answer()


@router.callback_query(IsAdminFilter(), Sub2SetupFSM.waiting_for_invite_url, F.data == "sub2_use_auto_link")
async def handle_use_auto_link(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Commit Sub 2 settings using the auto-generated link."""
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channel_type = data.get("channel_type")
    invite_url = data.get("invite_url")

    await SubscriptionRepository.set_sub2(
        channel_id=channel_id,
        channel_type=channel_type,
        invite_url=invite_url,
        is_enabled=True,
    )
    await state.clear()

    await callback.answer("✅ Sub 2 configured successfully!", show_alert=True)
    await handle_manage_sub_dashboard(callback, None)  # type: ignore


@router.message(IsAdminFilter(), Sub2SetupFSM.waiting_for_invite_url, F.text)
async def handle_sub2_manual_invite_link(message: types.Message, state: FSMContext) -> None:
    """Validate manual invite link and save Sub 2 configuration."""
    url_text = (message.text or "").strip()
    is_valid, err = validate_url(url_text)
    if not is_valid:
        await message.reply(f"⚠️ {err}\nPlease send a valid URL starting with https://:")
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    channel_type = data.get("channel_type", "public")

    await SubscriptionRepository.set_sub2(
        channel_id=channel_id,
        channel_type=channel_type,
        invite_url=url_text,
        is_enabled=True,
    )
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Subscriptions", callback_data="admin:manage_sub"))

    await message.answer(
        "🎉 <b>Sub 2 Configured Successfully!</b>\n\n"
        f"• <b>Channel ID:</b> <code>{channel_id}</code>\n"
        f"• <b>Mode:</b> {channel_type}\n"
        f"• <b>Invite URL:</b> {escape_html(url_text)}\n"
        "• <b>Status:</b> 🟢 Enabled\n\n"
        "Sub 2 is now active for all user movie verification checks.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# -------------------------------------------------------------
# 4. Toggle, Switch Type, Edit, and Remove Sub 2
# -------------------------------------------------------------
@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_toggle")
async def handle_sub2_toggle(callback: types.CallbackQuery) -> None:
    """Toggle Sub 2 enabled or disabled."""
    sub2 = await SubscriptionRepository.get_sub2()
    if not sub2:
        await callback.answer("❌ Sub 2 is not configured.", show_alert=True)
        return

    new_state = not sub2.get("is_enabled", False)
    await SubscriptionRepository.toggle_sub2_enabled(new_state)

    status_str = "Enabled" if new_state else "Disabled"
    await callback.answer(f"✅ Sub 2 is now {status_str}!", show_alert=False)
    await handle_manage_sub_dashboard(callback, None)  # type: ignore


@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_toggle_type")
async def handle_sub2_toggle_type(callback: types.CallbackQuery) -> None:
    """Switch Sub 2 mode between Public and Private Request."""
    sub2 = await SubscriptionRepository.get_sub2()
    if not sub2:
        await callback.answer("❌ Sub 2 is not configured.", show_alert=True)
        return

    current_type = sub2.get("channel_type", "public")
    new_type = "private_request" if current_type == "public" else "public"

    await SubscriptionRepository.update_sub2_type(new_type)
    type_str = "Private (Join Request)" if new_type == "private_request" else "Public"
    await callback.answer(f"✅ Sub 2 mode switched to: {type_str}", show_alert=True)
    await handle_manage_sub_dashboard(callback, None)  # type: ignore


@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_remove")
async def handle_sub2_remove(callback: types.CallbackQuery) -> None:
    """Remove Sub 2 configuration completely."""
    await SubscriptionRepository.remove_sub2()
    await callback.answer("🗑 Sub 2 removed. Only Sub 1 is now required.", show_alert=True)
    await handle_manage_sub_dashboard(callback, None)  # type: ignore


@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_edit_id")
async def handle_sub2_edit_id_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt for updated channel ID."""
    await state.set_state(Sub2SetupFSM.editing_channel_id)
    text = "✏️ <b>Change Sub 2 Channel ID</b>\n\nPlease send the new numeric channel ID:"
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_sub")
    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(IsAdminFilter(), Sub2SetupFSM.editing_channel_id, F.text)
async def handle_sub2_edit_id_input(message: types.Message, state: FSMContext) -> None:
    """Save updated channel ID."""
    is_valid, channel_id, err = validate_chat_id(message.text or "")
    if not is_valid or channel_id is None:
        await message.reply(f"⚠️ {err}\nPlease send a valid numeric channel ID:")
        return

    sub2 = await SubscriptionRepository.get_sub2()
    if sub2:
        await SubscriptionRepository.set_sub2(
            channel_id=channel_id,
            channel_type=sub2.get("channel_type", "public"),
            invite_url=sub2.get("invite_url", ""),
            is_enabled=sub2.get("is_enabled", True),
        )

    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Subscriptions", callback_data="admin:manage_sub"))
    await message.answer("✅ Sub 2 Channel ID updated!", reply_markup=builder.as_markup())


@router.callback_query(IsAdminFilter(), F.data == "adm_sub2_edit_url")
async def handle_sub2_edit_url_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Prompt for updated invite URL."""
    await state.set_state(Sub2SetupFSM.editing_invite_url)
    text = "🔗 <b>Change Sub 2 Invite URL</b>\n\nPlease send the new Telegram invite link:"
    cancel_kb = build_admin_cancel_keyboard(callback_data="admin:manage_sub")
    if callback.message:
        await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(IsAdminFilter(), Sub2SetupFSM.editing_invite_url, F.text)
async def handle_sub2_edit_url_input(message: types.Message, state: FSMContext) -> None:
    """Save updated invite URL."""
    url_text = (message.text or "").strip()
    is_valid, err = validate_url(url_text)
    if not is_valid:
        await message.reply(f"⚠️ {err}\nPlease send a valid URL starting with https://:")
        return

    await SubscriptionRepository.update_sub2_url(url_text)
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Back to Subscriptions", callback_data="admin:manage_sub"))
    await message.answer("✅ Sub 2 invite URL updated!", reply_markup=builder.as_markup())
