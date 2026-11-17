from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from obsidrop.config import AppConfig
from obsidrop.markdown_writer import CaptureError, render_markdown, write_capture
from tests.support import create_directory_link, remove_directory_link


def rendered_body(markdown: str) -> str:
    """Return the capture body after the YAML frontmatter block."""

    prefix = "---\n\n"
    return markdown.split(prefix, 1)[1]


class RenderMarkdownTests(unittest.TestCase):
    MOMENT = datetime(2026, 11, 17, 12, 15, 30, tzinfo=timezone(timedelta(hours=6)))

    def assert_rendered_body(self, content: str, expected: str) -> None:
        result = render_markdown(content, self.MOMENT)
        self.assertTrue(result.startswith("---\n"))
        self.assertEqual(rendered_body(result), expected)

    def test_renders_frontmatter_and_preserves_unicode(self) -> None:
        result = render_markdown("বাংলা note\nSecond line", self.MOMENT)

        self.assertIn('created: "2026-11-17T12:15:30+06:00"', result)
        self.assertIn("type: capture", result)
        self.assertIn("source: desktop", result)
        self.assertTrue(result.endswith("বাংলা note\nSecond line\n"))

    def test_single_line_without_trailing_newline(self) -> None:
        self.assert_rendered_body("A captured thought", "A captured thought\n")

    def test_single_line_with_one_trailing_newline(self) -> None:
        self.assert_rendered_body("A captured thought\n", "A captured thought\n")

    def test_preserves_multiple_trailing_newlines(self) -> None:
        self.assert_rendered_body("A captured thought\n\n", "A captured thought\n\n")
        self.assert_rendered_body("A captured thought\n\n\n", "A captured thought\n\n\n")

    def test_multiline_without_trailing_newline(self) -> None:
        self.assert_rendered_body("First line\nSecond line", "First line\nSecond line\n")

    def test_multiline_with_trailing_blank_line(self) -> None:
        self.assert_rendered_body(
            "First line\nSecond line\n\n",
            "First line\nSecond line\n\n",
        )

    def test_crlf_input_is_normalized_and_blank_lines_are_preserved(self) -> None:
        self.assert_rendered_body(
            "First line\r\nSecond line\r\n\r\n",
            "First line\nSecond line\n\n",
        )
        self.assert_rendered_body("First line\r\n", "First line\n")

    def test_lone_carriage_returns_are_normalized(self) -> None:
        self.assert_rendered_body("First\rSecond\r\r", "First\nSecond\n\n")

    def test_preserves_bangla_content_and_trailing_blank_line(self) -> None:
        self.assert_rendered_body(
            "বাংলা প্রথম লাইন\nদ্বিতীয় লাইন\n\n",
            "বাংলা প্রথম লাইন\nদ্বিতীয় লাইন\n\n",
        )

    def test_preserves_trailing_spaces_on_content_lines(self) -> None:
        self.assert_rendered_body("Line with spaces  ", "Line with spaces  \n")
        self.assert_rendered_body("Line\n\n", "Line\n\n")

    def test_rejects_empty_and_whitespace_only_content(self) -> None:
        for content in ("", "   ", "\n\t", "\r\n  \r\n", "\n\n\n"):
            with self.subTest(content=content):
                with self.assertRaises(CaptureError):
                    render_markdown(content)


class WriteCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.vault = self.base / "vault"
        self.vault.mkdir()
        self.vault = self.vault.resolve()
        self.config = AppConfig(str(self.vault), "Inbox/Quick Captures")
        self.moment = datetime(2026, 11, 17, 12, 15, 30, tzinfo=timezone(timedelta(hours=6)))

    def test_writes_note_to_configured_destination(self) -> None:
        path = write_capture(self.config, "A captured thought.", self.moment)

        self.assertEqual(path.parent, self.vault / "Inbox" / "Quick Captures")
        self.assertEqual(path.name, "2026-11-17-121530.md")
        self.assertIn("A captured thought.", path.read_text(encoding="utf-8"))

    def test_writes_exact_body_with_trailing_blank_lines(self) -> None:
        path = write_capture(self.config, "First line\n\n", self.moment)
        text = path.read_text(encoding="utf-8")

        self.assertTrue(text.endswith("---\n\nFirst line\n\n"))
        self.assertEqual(rendered_body(text), "First line\n\n")

    def test_collision_creates_unique_filename_without_overwriting(self) -> None:
        first = write_capture(self.config, "Original content", self.moment)
        original_bytes = first.read_bytes()
        second = write_capture(self.config, "Second content", self.moment)
        third = write_capture(self.config, "Third content", self.moment)

        self.assertEqual(first.name, "2026-11-17-121530.md")
        self.assertEqual(second.name, "2026-11-17-121530-01.md")
        self.assertEqual(third.name, "2026-11-17-121530-02.md")
        self.assertEqual(first.read_bytes(), original_bytes)
        self.assertIn("Second content", second.read_text(encoding="utf-8"))
        self.assertIn("Third content", third.read_text(encoding="utf-8"))

    def test_creates_nested_destination_directories(self) -> None:
        config = AppConfig(str(self.vault), "A/B/C")
        path = write_capture(config, "Nested", self.moment)

        self.assertEqual(path.parent, self.vault / "A" / "B" / "C")
        self.assertTrue(path.is_file())

    def test_rejects_empty_capture_without_creating_a_file(self) -> None:
        with self.assertRaises(CaptureError):
            write_capture(self.config, "   ", self.moment)
        self.assertFalse((self.vault / "Inbox").exists())

    def test_rejects_destinations_outside_vault(self) -> None:
        outside = self.base / "outside"
        for folder in ("../outside", "/outside", "C:/outside", r"\\server\share"):
            with self.subTest(folder=folder):
                with self.assertRaises(CaptureError):
                    write_capture(
                        AppConfig(str(self.vault), folder),
                        "Do not write outside",
                        self.moment,
                    )
        self.assertFalse(outside.exists())

    def test_rejects_invalid_destination_paths(self) -> None:
        for folder in ("Bad?Folder", "CON", "COM¹", "Inbox/Notes.", "Inbox/Notes "):
            with self.subTest(folder=folder):
                with self.assertRaises(CaptureError):
                    write_capture(
                        AppConfig(str(self.vault), folder),
                        "Invalid destination",
                        self.moment,
                    )

    def test_reports_directory_creation_failure(self) -> None:
        (self.vault / "Inbox").write_text("This is a file, not a folder.", encoding="utf-8")

        with self.assertRaises(CaptureError):
            write_capture(self.config, "Cannot be saved", self.moment)

        self.assertFalse((self.vault / "Inbox" / "Quick Captures").exists())

    def test_reports_file_write_failure_without_creating_a_note(self) -> None:
        destination = self.vault / "Inbox" / "Quick Captures"

        with mock.patch.object(Path, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(CaptureError):
                write_capture(self.config, "Cannot be written", self.moment)

        self.assertTrue(destination.is_dir())
        self.assertEqual(list(destination.glob("*.md")), [])

    def test_failed_write_does_not_overwrite_existing_note(self) -> None:
        destination = self.vault / "Inbox" / "Quick Captures"
        destination.mkdir(parents=True)
        existing = destination / "2026-11-17-121530.md"
        existing.write_bytes(b"original bytes that must survive")

        with mock.patch("obsidrop.markdown_writer.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(CaptureError):
                write_capture(self.config, "New content", self.moment)

        self.assertEqual(existing.read_bytes(), b"original bytes that must survive")

    def test_rejects_destination_link_outside_vault(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        link = self.vault / "Inbox"
        try:
            create_directory_link(link, outside)
            with self.assertRaises(CaptureError):
                write_capture(self.config, "Do not write outside", self.moment)
        finally:
            remove_directory_link(link)
        self.assertEqual(list(outside.iterdir()), [])

    def test_accepts_destination_link_inside_vault(self) -> None:
        real_destination = self.vault / "Real Inbox"
        real_destination.mkdir()
        link = self.vault / "Inbox"
        try:
            create_directory_link(link, real_destination)
            path = write_capture(self.config, "Inside the vault", self.moment)

            self.assertTrue(path.is_file())
            self.assertEqual(
                path.resolve().parent,
                (real_destination / "Quick Captures").resolve(),
            )
        finally:
            remove_directory_link(link)


if __name__ == "__main__":
    unittest.main()
