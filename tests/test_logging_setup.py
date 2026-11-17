from __future__ import annotations

import logging
import tempfile
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path

from obsidrop.logging_setup import configure_logging


class LoggingSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = logging.getLogger("obsidrop")
        self.original_handlers = list(self.logger.handlers)
        self.original_level = self.logger.level
        self.original_propagate = self.logger.propagate
        for handler in self.original_handlers:
            self.logger.removeHandler(handler)

    def tearDown(self) -> None:
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()
        for handler in self.original_handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(self.original_level)
        self.logger.propagate = self.original_propagate

    def make_temp_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_creates_a_single_rotating_file_handler(self) -> None:
        config_dir = self.make_temp_dir() / "Obsidrop"

        logger = configure_logging(config_dir)
        file_handlers = [
            handler for handler in logger.handlers
            if isinstance(handler, RotatingFileHandler)
        ]

        self.assertEqual(len(file_handlers), 1)
        self.assertFalse(any(isinstance(h, logging.NullHandler) for h in logger.handlers))

        logger.info("test message")
        file_handlers[0].flush()
        log_text = (config_dir / "logs" / "obsidrop.log").read_text(encoding="utf-8")
        self.assertIn("test message", log_text)

    def test_repeated_initialization_does_not_duplicate_output(self) -> None:
        config_dir = self.make_temp_dir() / "Obsidrop"

        configure_logging(config_dir)
        logger = configure_logging(config_dir)
        file_handlers = [
            handler for handler in logger.handlers
            if isinstance(handler, RotatingFileHandler)
        ]

        self.assertEqual(len(file_handlers), 1)
        logger.info("only once")
        file_handlers[0].flush()
        log_text = (config_dir / "logs" / "obsidrop.log").read_text(encoding="utf-8")
        self.assertEqual(log_text.count("only once"), 1)

    def test_recovers_after_log_directory_becomes_available(self) -> None:
        config_dir = self.make_temp_dir() / "Obsidrop"
        config_dir.write_text("not a directory", encoding="utf-8")

        logger = configure_logging(config_dir)
        self.assertTrue(any(isinstance(h, logging.NullHandler) for h in logger.handlers))
        self.assertFalse(any(isinstance(h, RotatingFileHandler) for h in logger.handlers))

        config_dir.unlink()
        logger = configure_logging(config_dir)
        file_handlers = [
            handler for handler in logger.handlers
            if isinstance(handler, RotatingFileHandler)
        ]

        self.assertEqual(len(file_handlers), 1)
        self.assertFalse(any(isinstance(h, logging.NullHandler) for h in logger.handlers))

        logger.info("recovered")
        file_handlers[0].flush()
        log_text = (config_dir / "logs" / "obsidrop.log").read_text(encoding="utf-8")
        self.assertIn("recovered", log_text)

    def test_failed_initialization_adds_only_one_null_handler(self) -> None:
        config_dir = self.make_temp_dir() / "Obsidrop"
        config_dir.write_text("not a directory", encoding="utf-8")

        configure_logging(config_dir)
        logger = configure_logging(config_dir)

        self.assertEqual(
            sum(isinstance(handler, logging.NullHandler) for handler in logger.handlers),
            1,
        )


if __name__ == "__main__":
    unittest.main()
