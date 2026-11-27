"""Administrator dashboard and control keyboards."""

from typing import Any, Dict, List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Build the comprehensive Administrator Dashboard with User Log Channel, Admin Management, and Advanced Broadcast."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎬 Add Movie", callback_data="admin:add_movie"),
        InlineKeyboardButton(text="📂 Manage Movies", callback_data="admin:manage_movies"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Menu Settings", callback_data="admin:menu_settings"),
        InlineKeyboardButton(text="📅 Manage Years", callback_data="admin:manage_years"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Add Sub (Sub 2)", callback_data="admin:manage_sub"),
        InlineKeyboardButton(text="📨 Advanced Broadcast", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Admin Management", callback_data="admin:manage_admins"),
        InlineKeyboardButton(text="📡 Log Channel Settings", callback_data="admin:log_channel"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Users", callback_data="admin:users"),
        InlineKeyboardButton(text="📊 Statistics", callback_data="admin:statistics"),
    )
    builder.row(
        InlineKeyboardButton(text="🔧 Bot Settings", callback_data="admin:bot_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Return to User View", callback_data="user_home"),
    )

    return builder.as_markup()


def build_admin_cancel_keyboard(callback_data: str = "admin:dashboard") -> InlineKeyboardMarkup:
    """Standard cancel button returning to dashboard or previous state."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel", callback_data=callback_data)
    return builder.as_markup()


def build_confirm_keyboard(
    confirm_callback: str,
    cancel_callback: str = "admin:dashboard",
) -> InlineKeyboardMarkup:
    """Confirmation keyboard with Yes / Cancel buttons."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=confirm_callback),
        InlineKeyboardButton(text="❌ Cancel", callback_data=cancel_callback),
    )
    return builder.as_markup()


# -------------------------------------------------------------
# Admin Management Keyboards
# -------------------------------------------------------------
def build_admin_management_keyboard() -> InlineKeyboardMarkup:
    """Admin Management overview keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Add Admin", callback_data="adm_add_admin"),
        InlineKeyboardButton(text="➖ Remove Admin", callback_data="adm_remove_admin_list"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 View All Admins", callback_data="adm_view_admins"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )
    return builder.as_markup()


def build_remove_admins_keyboard(
    admins: List[Dict[str, Any]],
    protected_owner_id: int,
) -> InlineKeyboardMarkup:
    """Build list of removable administrators."""
    builder = InlineKeyboardBuilder()

    for adm in admins:
        admin_id = adm.get("admin_id")
        role = adm.get("role", "admin")
        if admin_id == protected_owner_id:
            # Protected owner cannot be removed
            continue

        builder.row(
            InlineKeyboardButton(
                text=f"🗑 Remove Admin: {admin_id} ({role})",
                callback_data=f"adm_rm_select:{admin_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Back to Admin Management", callback_data="admin:manage_admins"),
    )
    return builder.as_markup()


# -------------------------------------------------------------
# User Log Channel Keyboards
# -------------------------------------------------------------
def build_log_channel_settings_keyboard(config: Dict[str, Any]) -> InlineKeyboardMarkup:
    """User Log Channel settings control keyboard."""
    builder = InlineKeyboardBuilder()

    is_enabled = config.get("is_enabled", False)
    status_text = "🔴 Disable Log Channel" if is_enabled else "🟢 Enable Log Channel"

    log_activities = config.get("log_activities", False)
    act_text = "🔕 Activity Logs: OFF" if not log_activities else "🔔 Activity Logs: ON"

    builder.row(
        InlineKeyboardButton(text="✏️ Configure Channel ID", callback_data="adm_logch_set_id"),
        InlineKeyboardButton(text="🧪 Test Connection", callback_data="adm_logch_test"),
    )
    builder.row(
        InlineKeyboardButton(text=status_text, callback_data="adm_logch_toggle"),
        InlineKeyboardButton(text=act_text, callback_data="adm_logch_toggle_activities"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )
    return builder.as_markup()


# -------------------------------------------------------------
# Advanced Broadcast Keyboards
# -------------------------------------------------------------
def build_broadcast_collection_keyboard(collected_count: int) -> InlineKeyboardMarkup:
    """Advanced broadcast message collection keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Add More Messages", callback_data="bcast_add_more"),
        InlineKeyboardButton(text=f"👁 Preview ({collected_count})", callback_data="bcast_preview"),
    )
    builder.row(
        InlineKeyboardButton(text="🚀 SEND THIS MESSAGE", callback_data="bcast_confirm_send"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel Broadcast", callback_data="admin:dashboard"),
    )
    return builder.as_markup()


# -------------------------------------------------------------
# Dynamic Menu Settings Keyboards
# -------------------------------------------------------------
def build_menu_settings_overview_keyboard(
    buttons: List[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """List all 4 customizable menu buttons for editing."""
    builder = InlineKeyboardBuilder()

    for btn in buttons:
        status_icon = "🟢" if btn.get("is_enabled", True) else "🔴"
        order = btn.get("order", 0)
        title = btn.get("title", "Button")
        key = btn.get("button_key")
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} [#{order}] {title}",
                callback_data=f"adm_menu_edit:{key}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔄 Restore Defaults", callback_data="adm_menu_restore"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    return builder.as_markup()


def build_menu_button_detail_keyboard(
    button: Dict[str, Any],
) -> InlineKeyboardMarkup:
    """Action buttons to edit title, URL, order, and status of a menu button."""
    builder = InlineKeyboardBuilder()
    key = button["button_key"]
    is_enabled = button.get("is_enabled", True)
    is_external = button.get("is_external", False)

    status_text = "🔴 Disable Button" if is_enabled else "🟢 Enable Button"

    builder.row(
        InlineKeyboardButton(text="✏️ Edit Title", callback_data=f"adm_btn_title:{key}"),
        InlineKeyboardButton(text="🔢 Change Order", callback_data=f"adm_btn_order:{key}"),
    )

    if is_external:
        builder.row(
            InlineKeyboardButton(text="🔗 Update Link / URL", callback_data=f"adm_btn_url:{key}"),
        )

    builder.row(
        InlineKeyboardButton(text=status_text, callback_data=f"adm_btn_toggle:{key}"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Menu Settings", callback_data="admin:menu_settings"),
    )

    return builder.as_markup()


def build_sub2_management_keyboard(
    sub2: Optional[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Sub 2 channel configuration keyboard."""
    builder = InlineKeyboardBuilder()

    if sub2:
        is_enabled = sub2.get("is_enabled", False)
        status_text = "🔴 Disable Sub 2" if is_enabled else "🟢 Enable Sub 2"
        channel_type = sub2.get("channel_type", "public")
        type_toggle_text = "Switch to Private (Join Request)" if channel_type == "public" else "Switch to Public"

        builder.row(
            InlineKeyboardButton(text=status_text, callback_data="adm_sub2_toggle"),
        )
        builder.row(
            InlineKeyboardButton(text=f"🔄 {type_toggle_text}", callback_data="adm_sub2_toggle_type"),
        )
        builder.row(
            InlineKeyboardButton(text="✏️ Change Channel ID", callback_data="adm_sub2_edit_id"),
            InlineKeyboardButton(text="🔗 Change Invite Link", callback_data="adm_sub2_edit_url"),
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Remove Sub 2", callback_data="adm_sub2_remove"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="➕ Setup Sub 2 Channel", callback_data="adm_sub2_setup"),
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    return builder.as_markup()


def build_years_management_keyboard(
    years: List[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Manage release years keyboard."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Add New Year", callback_data="adm_yr_add"),
    )

    for y in years:
        year_val = y.get("year")
        is_enabled = y.get("is_enabled", True)
        icon = "🟢" if is_enabled else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} Year {year_val}",
                callback_data=f"adm_yr_manage:{year_val}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="admin:dashboard"),
    )

    return builder.as_markup()


def build_single_year_actions_keyboard(
    year: int,
    is_enabled: bool,
    movie_count: int,
) -> InlineKeyboardMarkup:
    """Actions for a single release year."""
    builder = InlineKeyboardBuilder()

    status_text = "🔴 Disable Year" if is_enabled else "🟢 Enable Year"

    builder.row(
        InlineKeyboardButton(text=status_text, callback_data=f"adm_yr_toggle:{year}"),
        InlineKeyboardButton(text="✏️ Rename Year", callback_data=f"adm_yr_rename:{year}"),
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🗑 Delete Year ({movie_count} movies)",
            callback_data=f"adm_yr_del:{year}",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Back to Years", callback_data="admin:manage_years"),
    )

    return builder.as_markup()
