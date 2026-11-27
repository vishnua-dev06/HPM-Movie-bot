"""Unit tests for administrator authentication and authorization enforcement supporting multiple admins."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message, User
from config import settings
from database.admins import AdminRepository
from middlewares.admin_auth import AdminAuthMiddleware, IsAdminFilter


@pytest.mark.asyncio
async def test_is_admin_filter_matches_primary_admin():
    """Verify IsAdminFilter returns True for configured primary ADMIN_ID."""
    admin_filter = IsAdminFilter()

    admin_user = User(id=settings.primary_admin_id, is_bot=False, first_name="Owner")
    mock_message = MagicMock(spec=Message)
    mock_message.from_user = admin_user

    result = await admin_filter(mock_message)
    assert result is True


@pytest.mark.asyncio
async def test_is_admin_filter_matches_dynamically_added_secondary_admin():
    """Verify IsAdminFilter returns True for second administrator added to database."""
    admin_filter = IsAdminFilter()
    secondary_admin_id = 444333222

    await AdminRepository.add_admin(secondary_admin_id, added_by=settings.primary_admin_id)

    secondary_user = User(id=secondary_admin_id, is_bot=False, first_name="SecondaryAdmin")
    mock_message = MagicMock(spec=Message)
    mock_message.from_user = secondary_user

    result = await admin_filter(mock_message)
    assert result is True


@pytest.mark.asyncio
async def test_is_admin_filter_rejects_non_admin():
    """Verify IsAdminFilter returns False for any non-admin user."""
    admin_filter = IsAdminFilter()

    normal_user = User(id=12345678, is_bot=False, first_name="RegularUser")
    mock_message = MagicMock(spec=Message)
    mock_message.from_user = normal_user

    result = await admin_filter(mock_message)
    assert result is False


@pytest.mark.asyncio
async def test_admin_auth_middleware_blocks_unauthorized_callback():
    """Verify AdminAuthMiddleware denies unauthorized admin callback queries."""
    middleware = AdminAuthMiddleware()

    handler = AsyncMock()
    unauthorized_user = User(id=88888888, is_bot=False, first_name="Intruder")

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = unauthorized_user
    mock_callback.data = "admin:dashboard"
    mock_callback.answer = AsyncMock()

    result = await middleware(handler, mock_callback, {})

    # Handler must NOT be executed
    handler.assert_not_called()
    mock_callback.answer.assert_called_once_with(
        "❌ Access denied: Administrator only.",
        show_alert=True,
    )
    assert result is None


@pytest.mark.asyncio
async def test_admin_auth_middleware_allows_authorized_callback():
    """Verify AdminAuthMiddleware permits callback execution for authorized admins."""
    middleware = AdminAuthMiddleware()

    handler = AsyncMock(return_value="executed_ok")
    admin_user = User(id=settings.primary_admin_id, is_bot=False, first_name="Boss")

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = admin_user
    mock_callback.data = "admin:dashboard"

    result = await middleware(handler, mock_callback, {})

    handler.assert_called_once()
    assert result == "executed_ok"


@pytest.mark.asyncio
async def test_admin_auth_middleware_blocks_unauthorized_admin_command():
    """Verify AdminAuthMiddleware blocks /admin command for normal users."""
    middleware = AdminAuthMiddleware()

    handler = AsyncMock()
    normal_user = User(id=55555555, is_bot=False, first_name="User")

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = normal_user
    mock_msg.text = "/admin"
    mock_msg.reply = AsyncMock()

    result = await middleware(handler, mock_msg, {})

    handler.assert_not_called()
    mock_msg.reply.assert_called_once_with("❌ Access denied.")
    assert result is None
