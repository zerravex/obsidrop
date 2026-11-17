"""Small rotating log setup for diagnosing application problems."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(config_dir: Path) -> logging.Logger:
    """Configure a rotating log file outside the user's vault."""

    logger = logging.getLogger("obsidrop")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    try:
        log_dir = config_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "obsidrop.log",
            maxBytes=512 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
    except OSError:
        # Logging must not prevent the user from capturing notes when the
        # configuration directory is temporarily unavailable.
        logger.addHandler(logging.NullHandler())

    return logger
