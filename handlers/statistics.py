"""Administrator statistics and user management views."""

from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.activity_logs import ActivityLogRepository
from database.users import UserRepository
from middlewares.admin_auth import IsAdminFilter
from services.statistics_service import StatisticsService
from utils.helpers import escape_html, format_datetime, format_number

router = Router(name="statistics_router")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


# 1. Statistics Dashboard
@router.callback_query(F.data == "admin:statistics")
async def handle_statistics_view(callback: types.CallbackQuery) -> None:
    """Display real-time aggregated statistics from MongoDB collections."""
    stats = await StatisticsService.get_overview_statistics()
    recent_logs = await ActivityLogRepository.get_recent_activity(limit=5)

    recent_activity_lines = []
    if recent_logs:
        for log in recent_logs:
            action = log.get("action", "unknown").replace("_", " ").title()
            user_id = log.get("user_id", "N/A")
            time_str = format_datetime(log.get("created_at"))
            recent_activity_lines.append(f"• <b>{action}</b> by <code>{user_id}</code> at {time_str}")
    else:
        recent_activity_lines.append("• No recent activity recorded.")

    activity_text = "\n".join(recent_activity_lines)

    text = (
        "📊 <b>Master Bot Statistics Dashboard</b>\n\n"
        "<b>👥 User Metrics:</b>\n"
        f"• Total Registered Users: <b>{format_number(stats['total_users'])}</b>\n"
        f"• Active Users: <b>{format_number(stats['active_users'])}</b>\n"
        f"• Blocked Users: <b>{format_number(stats['blocked_users'])}</b>\n"
        f"• Today's New Users: <b>{format_number(stats['today_new_users'])}</b>\n\n"
        "<b>🎬 Movie Catalog Metrics:</b>\n"
        f"• Total Movies: <b>{format_number(stats['total_movies'])}</b>\n"
        f"• Latest Malayalam: <b>{format_number(stats['latest_movies'])}</b>\n"
        f"• Malayalam Dubbed: <b>{format_number(stats['dubbed_movies'])}</b>\n"
        f"• Available Release Years: <b>{stats['total_years']}</b>\n"
        f"• Stored Media Files: <b>{format_number(stats['total_media'])}</b>\n\n"
        "<b>📢 Operations & System:</b>\n"
        f"• Authorized Admins: <b>{stats['total_admins']}</b>\n"
        f"• User Log Channel: {stats['log_status']}\n"
        f"• Sub 2 Channel: {stats['sub2_status']}\n"
        f"• Broadcasts Executed: <b>{stats['total_broadcasts']}</b>\n\n"
        f"<b>🕒 Recent Activity:</b>\n{activity_text}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh Statistics", callback_data="admin:statistics"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# 2. User Management View
@router.callback_query(F.data == "admin:users")
async def handle_users_view(callback: types.CallbackQuery) -> None:
    """Display user management metrics and recent registrations."""
    total_users = await UserRepository.get_total_users_count()
    active_users = await UserRepository.get_active_users_count()
    blocked_users = await UserRepository.get_blocked_users_count()
    today_users = await UserRepository.get_today_new_users_count()
    recent_users = await UserRepository.get_recent_users(limit=10)

    user_rows = []
    for u in recent_users:
        uid = u.get("user_id")
        fname = escape_html(u.get("first_name", "Unknown"))
        uname = f"@{u.get('username')}" if u.get("username") else "No username"
        joined = format_datetime(u.get("first_started_at") or u.get("joined_at"))
        status_icon = "🟢" if not u.get("is_blocked") else "🔴"
        user_rows.append(f"{status_icon} <b>{fname}</b> (<code>{uid}</code>) — {uname}\n   <i>Joined: {joined}</i>")

    users_list_text = "\n".join(user_rows) if user_rows else "No users registered yet."

    text = (
        "👥 <b>User Management Overview</b>\n\n"
        f"• Total Registered: <b>{format_number(total_users)}</b>\n"
        f"• Active Users: <b>{format_number(active_users)}</b>\n"
        f"• Blocked / Inaccessible: <b>{format_number(blocked_users)}</b>\n"
        f"• Today's Registrations: <b>{format_number(today_users)}</b>\n\n"
        f"<b>📋 Recent 10 Registrations:</b>\n{users_list_text}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh Users", callback_data="admin:users"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()
