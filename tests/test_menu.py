"""Unit and integration tests for dynamic main menu customization."""

import pytest
from database.settings import MenuSettingsRepository
from keyboards.user import build_user_main_menu


@pytest.mark.asyncio
async def test_menu_default_seeding_and_retrieval():
    """Verify menu seeding initializes all 4 default buttons."""
    buttons = await MenuSettingsRepository.get_all_buttons()
    assert len(buttons) == 4

    keys = [b["button_key"] for b in buttons]
    assert "latest_movies" in keys
    assert "dubbed_movies" in keys
    assert "search_group" in keys
    assert "main_channel" in keys


@pytest.mark.asyncio
async def test_update_button_title_and_order():
    """Verify administrator can edit button label and change display order."""
    await MenuSettingsRepository.get_all_buttons()

    # Update title
    await MenuSettingsRepository.update_title(
        button_key="latest_movies",
        title="🌟 Top Malayalam Cinema",
    )
    btn = await MenuSettingsRepository.get_button("latest_movies")
    assert btn["title"] == "🌟 Top Malayalam Cinema"

    # Update order
    await MenuSettingsRepository.update_order(button_key="latest_movies", order=4)
    btn_reordered = await MenuSettingsRepository.get_button("latest_movies")
    assert btn_reordered["order"] == 4


@pytest.mark.asyncio
async def test_toggle_button_enabled_status():
    """Verify disabling a button hides it from active buttons list."""
    await MenuSettingsRepository.get_all_buttons()

    # Disable search group button
    await MenuSettingsRepository.toggle_enabled(button_key="search_group", is_enabled=False)

    active_buttons = await MenuSettingsRepository.get_active_buttons()
    active_keys = [b["button_key"] for b in active_buttons]

    assert "search_group" not in active_keys
    assert len(active_buttons) == 3


@pytest.mark.asyncio
async def test_update_external_url():
    """Verify administrator can update group and channel links."""
    await MenuSettingsRepository.get_all_buttons()

    new_url = "https://t.me/new_malayalam_movies_channel"
    await MenuSettingsRepository.update_url(button_key="main_channel", url=new_url)

    btn = await MenuSettingsRepository.get_button("main_channel")
    assert btn["url"] == new_url


@pytest.mark.asyncio
async def test_restore_menu_to_defaults():
    """Verify restoring defaults brings back original labels and ordering."""
    await MenuSettingsRepository.get_all_buttons()

    # Modify button
    await MenuSettingsRepository.update_title("latest_movies", "Temporary Modified Title")
    await MenuSettingsRepository.toggle_enabled("search_group", False)

    # Restore defaults
    await MenuSettingsRepository.reset_to_defaults()

    restored_latest = await MenuSettingsRepository.get_button("latest_movies")
    assert restored_latest["title"] == "🎬 Latest Malayalam Movies"

    restored_search = await MenuSettingsRepository.get_button("search_group")
    assert restored_search["is_enabled"] is True


def test_user_main_menu_keyboard_rendering():
    """Verify inline keyboard builder properly converts active button documents."""
    fake_buttons = [
        {"button_key": "latest_movies", "title": "🎬 Latest", "url": None, "is_enabled": True, "order": 1},
        {"button_key": "dubbed_movies", "title": "🎥 Dubbed", "url": None, "is_enabled": True, "order": 2},
        {"button_key": "search_group", "title": "🔎 Group", "url": "https://t.me/group", "is_enabled": True, "order": 3},
        {"button_key": "main_channel", "title": "📢 Channel", "url": "https://t.me/channel", "is_enabled": False, "order": 4},
    ]

    kb = build_user_main_menu(buttons=fake_buttons, is_admin=False)
    # Channel was disabled, so exactly 3 buttons should be rendered
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    assert len(all_buttons) == 3
    assert all_buttons[0].text == "🎬 Latest"
    assert all_buttons[0].callback_data == "cat:latest"
    assert all_buttons[1].text == "🎥 Dubbed"
    assert all_buttons[1].callback_data == "cat:dubbed"
    assert all_buttons[2].text == "🔎 Group"
    assert all_buttons[2].url == "https://t.me/group"
