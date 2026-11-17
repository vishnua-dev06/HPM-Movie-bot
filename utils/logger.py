"""Logging configuration with secret masking."""

import logging
import re
import sys
from typing import Optional


class SensitiveFilter(logging.Filter):
    """Filter that masks bot tokens and mongodb passwords in log messages."""

    # Matches Telegram bot token pattern: 123456789:ABC...
    TOKEN_PATTERN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")
    # Matches Mongo URI passwords: mongodb+srv://user:pass@host
    MONGO_PATTERN = re.compile(r"://([^:]+):([^@]+)@")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_PATTERN.sub("[REDACTED_BOT_TOKEN]", record.msg)
            record.msg = self.MONGO_PATTERN.sub(r"://\1:***@", record.msg)
        return True


def setup_logger(name: str = "MalayalamMovieBot", level: int = logging.INFO) -> logging.Logger:
    """Configure and return application logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(module)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveFilter())

        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()
