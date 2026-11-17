"""General helper functions for data formatting and sanitization."""

import html
from datetime import datetime, timezone
from typing import Optional


def escape_html(text: Optional[str]) -> str:
    """Escape special characters for safe Telegram HTML parsing."""
    if not text:
        return ""
    return html.escape(str(text))


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime object into human-readable string."""
    if not dt:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def format_number(n: int) -> str:
    """Format integers with comma separators (e.g. 10,000)."""
    return f"{n:,}"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if length exceeds max_length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
