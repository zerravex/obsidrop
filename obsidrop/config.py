"""Application configuration and safe vault-path validation."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


DEFAULT_CAPTURE_FOLDER = "Inbox/Quick Captures"
CONFIG_SCHEMA_VERSION = 1


class ConfigError(ValueError):
    """Raised when application configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    """Settings required by the capture application."""

    vault_path: str
    capture_folder: str = DEFAULT_CAPTURE_FOLDER


def get_config_dir() -> Path:
    """Return Obsidrop's per-user configuration directory."""

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Obsidrop"
        return Path.home() / "AppData" / "Roaming" / "Obsidrop"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "Obsidrop"
    return Path.home() / ".config" / "Obsidrop"


def get_legacy_config_dir() -> Path:
    """Return the old VaultDrop config path for one-time settings migration."""

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "VaultDrop"
        return Path.home() / "AppData" / "Roaming" / "VaultDrop"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "VaultDrop"
    return Path.home() / ".config" / "VaultDrop"


def validate_capture_folder(capture_folder: str) -> str:
    """Validate and normalize a vault-relative destination folder.

    Both slash styles are accepted so a configuration copied between Windows
    machines remains readable. Absolute paths, parent traversal, drive names,
    Windows-reserved names, and invalid Windows filename characters are rejected.
    """

    if not isinstance(capture_folder, str):
        raise ConfigError("The capture folder must be text.")

    if capture_folder != capture_folder.rstrip():
        raise ConfigError("The capture folder cannot end with whitespace.")

    raw = capture_folder.strip()
    if not raw:
        raise ConfigError("Enter a destination folder inside your vault.")

    windows_path = PureWindowsPath(raw)
    if windows_path.is_absolute() or windows_path.drive or raw.startswith(("/", "\\")):
        raise ConfigError("The capture folder must be relative to your vault.")

    normalized = raw.replace("\\", "/")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ConfigError("The capture folder cannot contain empty, '.' or '..' path segments.")

    reserved_names = {
        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
        # Windows 11 also treats these superscript variants as device names.
        "COM¹", "COM²", "COM³",
        "LPT¹", "LPT²", "LPT³",
    }
    invalid_characters = set('<>:"|?*')

    for part in parts:
        if any(ord(char) < 32 or char in invalid_characters for char in part):
            raise ConfigError(f"The folder name {part!r} contains characters Windows does not allow.")
        if part.endswith((" ", ".")):
            raise ConfigError(f"The folder name {part!r} cannot end with a space or period.")
        # Windows ignores trailing spaces before the extension and compares
        # device names case-insensitively.
        base_name = part.split(".", 1)[0].rstrip(" .").upper()
        if base_name in reserved_names:
            raise ConfigError(f"The folder name {part!r} is reserved by Windows.")

    return "/".join(parts)


def validate_config(vault_path: str, capture_folder: str) -> AppConfig:
    """Validate a selected vault and a destination contained within it."""

    if not isinstance(vault_path, str) or not vault_path.strip():
        raise ConfigError("Choose your Obsidian vault folder first.")

    vault = Path(vault_path).expanduser()
    try:
        vault = vault.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ConfigError(f"The selected vault folder cannot be accessed: {exc}") from exc

    if not vault.is_dir():
        raise ConfigError("The selected vault path is not a folder.")

    normalized_folder = validate_capture_folder(capture_folder)
    destination = vault.joinpath(*normalized_folder.split("/"))

    try:
        resolved_destination = destination.resolve(strict=False)
        resolved_destination.relative_to(vault)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ConfigError("The destination folder must remain inside the selected vault.") from exc

    return AppConfig(vault_path=str(vault), capture_folder=normalized_folder)


class ConfigStore:
    """Load and save Obsidrop settings outside the Obsidian vault.

    When using the default per-user location, the store can migrate an existing
    VaultDrop config file into the new Obsidrop config directory. The legacy file
    is copied by saving the validated settings; it is not deleted or modified.
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        legacy_config_dir: Path | None = None,
    ) -> None:
        use_default_location = config_dir is None
        self.config_dir = config_dir or get_config_dir()
        self.legacy_config_dir = (
            legacy_config_dir
            if legacy_config_dir is not None
            else get_legacy_config_dir() if use_default_location else None
        )
        self.config_file = self.config_dir / "config.json"

    def load(self) -> AppConfig | None:
        """Load settings, migrating the old app config folder when appropriate."""

        source_file = self.config_file
        migrating_legacy_config = False
        if not source_file.exists():
            legacy_file = (
                self.legacy_config_dir / "config.json"
                if self.legacy_config_dir is not None
                else None
            )
            if legacy_file is None or not legacy_file.is_file():
                return None
            source_file = legacy_file
            migrating_legacy_config = True

        try:
            raw: Any = json.loads(source_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(
                f"Obsidrop could not read its settings file: {exc}. "
                "You can choose your vault again and save new settings."
            ) from exc

        if not isinstance(raw, dict):
            raise ConfigError("The settings file has an invalid structure. Choose your vault again.")

        version = raw.get("schema_version")
        # bool is a subclass of int in Python, and JSON numbers such as 1.0
        # compare equal to 1. Require the exact integer type so malformed or
        # future schema markers are not silently accepted.
        if type(version) is not int or version != CONFIG_SCHEMA_VERSION:
            raise ConfigError(
                f"Unsupported settings version ({version!r}). "
                f"This v0.0.1 build expects settings version {CONFIG_SCHEMA_VERSION}."
            )

        try:
            config = validate_config(
                vault_path=raw.get("vault_path", ""),
                capture_folder=raw.get("capture_folder", DEFAULT_CAPTURE_FOLDER),
            )
        except ConfigError as exc:
            raise ConfigError(f"Saved settings need attention: {exc}") from exc

        if migrating_legacy_config:
            # Save into the new folder; deliberately leave the old file intact.
            self.save(config)

        return config

    def save(self, config: AppConfig) -> None:
        """Persist validated settings using an atomic replace."""

        checked = validate_config(config.vault_path, config.capture_folder)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": CONFIG_SCHEMA_VERSION,
            **asdict(checked),
        }

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.config_dir,
                prefix="config-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, self.config_file)
        except OSError as exc:
            raise ConfigError(f"Could not save Obsidrop settings: {exc}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
