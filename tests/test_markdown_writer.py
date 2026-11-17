from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from obsidrop.config import AppConfig
from obsidrop.markdown_writer import CaptureError, render_markdown, write_capture


class RenderMarkdownTests(unittest.TestCase):
    def test_renders_frontmatter_and_preserves_unicode(self) -> None:
        moment = datetime(2026, 11, 17, 12, 15, 30, tzinfo=timezone(timedelta(hours=6)))
        result = render_markdown("বাংলা note\nSecond line", moment)

        self.assertIn('created: "2026-11-17T12:15:30+06:00"', result)
        self.assertIn("type: capture", result)
        self.assertIn("source: desktop", result)
        self.assertTrue(result.endswith("বাংলা note\nSecond line\n"))

    def test_rejects_blank_content(self) -> None:
        for content in ("", "   ", "\n\t"):
            with self.subTest(content=content):
                with self.assertRaises(CaptureError):
                    render_markdown(content)


class WriteCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name) / "vault"
        self.vault.mkdir()
        self.config = AppConfig(str(self.vault), "Inbox/Quick Captures")
        self.moment = datetime(2026, 11, 17, 12, 15, 30, tzinfo=timezone(timedelta(hours=6)))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_writes_note_to_configured_destination(self) -> None:
        path = write_capture(self.config, "A captured thought.", self.moment)

        self.assertEqual(path.parent, self.vault / "Inbox" / "Quick Captures")
        self.assertEqual(path.name, "2026-11-17-121530.md")
        self.assertIn("A captured thought.", path.read_text(encoding="utf-8"))

    def test_collision_creates_unique_filename_without_overwriting(self) -> None:
        first = write_capture(self.config, "Original content", self.moment)
        second = write_capture(self.config, "Second content", self.moment)

        self.assertEqual(first.name, "2026-11-17-121530.md")
        self.assertEqual(second.name, "2026-11-17-121530-01.md")
        self.assertIn("Original content", first.read_text(encoding="utf-8"))
        self.assertIn("Second content", second.read_text(encoding="utf-8"))

    def test_rejects_empty_capture_without_creating_a_file(self) -> None:
        with self.assertRaises(CaptureError):
            write_capture(self.config, "   ", self.moment)
        self.assertFalse((self.vault / "Inbox").exists())

    def test_rejects_symlink_destination_outside_vault(self) -> None:
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        inbox = self.vault / "Inbox"
        try:
            inbox.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks are unavailable on this system.")

        with self.assertRaises(CaptureError):
            write_capture(self.config, "Do not write outside", self.moment)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
