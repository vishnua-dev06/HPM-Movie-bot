"""Input validation helpers for Telegram bot."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


def validate_chat_id(val: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate a Telegram chat/channel ID string."""
    try:
        val_clean = val.strip()
        chat_id = int(val_clean)
        # Channel IDs normally start with -100, but supergroups/groups can also start with -
        return True, chat_id, None
    except (ValueError, TypeError):
        return False, None, "Invalid Telegram ID. It must be a valid integer (e.g. -1001234567890)."


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format, especially Telegram links."""
    clean_url = url.strip()
    try:
        result = urlparse(clean_url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL. Please include https:// (e.g., https://t.me/channel)."
        if result.scheme not in ("http", "https"):
            return False, "URL scheme must be http or https."
        return True, None
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"


def validate_year(year_str: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate a 4-digit release year."""
    try:
        year = int(year_str.strip())
        if 1900 <= year <= 2100:
            return True, year, None
        return False, None, "Year must be between 1900 and 2100."
    except (ValueError, TypeError):
        return False, None, "Year must be a 4-digit integer (e.g., 2026)."


def validate_movie_title(title: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate movie title string."""
    clean_title = title.strip()
    if not clean_title:
        return False, None, "Movie title cannot be empty."
    if len(clean_title) > 150:
        return False, None, "Movie title is too long (maximum 150 characters)."
    return True, clean_title, None
