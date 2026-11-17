"""Create timestamped Markdown captures inside a configured vault."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .config import AppConfig, ConfigError, validate_config


class CaptureError(RuntimeError):
    """Raised when a capture cannot be safely written."""


def render_markdown(content: str, created_at: datetime | None = None) -> str:
    """Render a capture as Markdown with a small YAML frontmatter block."""

    if not isinstance(content, str) or not content.strip():
        raise CaptureError("Write something before saving the capture.")

    moment = created_at or datetime.now().astimezone()
    if moment.tzinfo is None:
        moment = moment.astimezone()
    timestamp = moment.isoformat(timespec="seconds")
    # JSON double-quoted strings are valid YAML scalars and safely quote the timestamp.
    # Normalize line endings and ensure exactly one final newline without removing
    # intentional trailing blank lines from the user's content.
    body = content.replace("\r\n", "\n").replace("\r", "\n")
    if body.endswith("\n"):
        body = body[:-1]
    return (
        "---\n"
        f"created: {json.dumps(timestamp)}\n"
        "type: capture\n"
        "source: desktop\n"
        "---\n\n"
        f"{body}\n"
    )


def _ensure_inside_vault(vault: Path, destination: Path) -> None:
    """Raise if a resolved destination escapes the selected vault."""

    try:
        destination.resolve(strict=True).relative_to(vault.resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as exc:
        raise CaptureError(
            "The capture destination is outside the selected vault or cannot be accessed. "
            "Check the destination folder and any folder shortcuts/symlinks."
        ) from exc


def write_capture(
    config: AppConfig,
    content: str,
    created_at: datetime | None = None,
) -> Path:
    """Write one unique Markdown file and return its path.

    Files are opened in exclusive-create mode (``x``), so an existing note is
    never overwritten, including in the event of a filename collision.
    """

    if not isinstance(content, str) or not content.strip():
        raise CaptureError("Write something before saving the capture.")

    try:
        checked = validate_config(config.vault_path, config.capture_folder)
    except ConfigError as exc:
        raise CaptureError(str(exc)) from exc

    vault = Path(checked.vault_path).resolve(strict=True)
    destination = vault.joinpath(*checked.capture_folder.split("/"))

    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CaptureError(f"Could not create the capture folder: {exc}") from exc

    _ensure_inside_vault(vault, destination)

    moment = created_at or datetime.now().astimezone()
    if moment.tzinfo is None:
        # Treat explicitly supplied naive timestamps as local time.
        moment = moment.astimezone()
    filename_base = moment.strftime("%Y-%m-%d-%H%M%S")
    markdown = render_markdown(content, moment)

    for suffix_number in range(0, 10_000):
        suffix = "" if suffix_number == 0 else f"-{suffix_number:02d}"
        target = destination / f"{filename_base}{suffix}.md"
        try:
            # Exclusive creation is atomic with respect to competing processes.
            with target.open("x", encoding="utf-8", newline="\n") as note_file:
                note_file.write(markdown)
                note_file.flush()
                os.fsync(note_file.fileno())
            return target
        except FileExistsError:
            continue
        except OSError as exc:
            raise CaptureError(
                f"Could not write the capture file: {exc}. "
                "The application did not overwrite an existing note."
            ) from exc

    raise CaptureError("Could not find an unused filename after 10,000 attempts.")
