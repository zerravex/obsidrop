"""Small rotating log setup for diagnosing application problems."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(config_dir: Path) -> logging.Logger:
    """Configure a rotating log file outside the user's vault.

    Calling this again after an earlier failure can recover once the log
    directory becomes available. Existing file handlers are reused so repeated
    calls never duplicate log output.
    """

    logger = logging.getLogger("obsidrop")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
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
        # configuration directory is temporarily unavailable. A caller may
        # invoke this function again later to recover.
        if not any(isinstance(existing, logging.NullHandler) for existing in logger.handlers):
            logger.addHandler(logging.NullHandler())
        return logger

    # Remove the fallback handler(s) from an earlier failed initialization.
    for existing in list(logger.handlers):
        if isinstance(existing, logging.NullHandler):
            logger.removeHandler(existing)
            existing.close()

    return logger
