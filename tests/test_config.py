from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from obsidrop.config import (
    DEFAULT_CAPTURE_FOLDER,
    AppConfig,
    ConfigError,
    ConfigStore,
    validate_capture_folder,
    validate_config,
)
from tests.support import create_directory_link, remove_directory_link


class ValidateCaptureFolderTests(unittest.TestCase):
    def test_normalizes_backslashes(self) -> None:
        self.assertEqual(
            validate_capture_folder(r"Inbox\Quick Captures"),
            "Inbox/Quick Captures",
        )

    def test_rejects_empty_folder(self) -> None:
        for value in ("", "  ", "\t\n"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_parent_traversal(self) -> None:
        for value in ("../outside", "Inbox/../../outside", r"Inbox\..\outside"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_absolute_and_drive_paths(self) -> None:
        for value in ("/outside", r"C:\outside", r"\\server\share", "C:/outside"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_common_reserved_names(self) -> None:
        for value in (
            "CON",
            "con",
            "PrN",
            "AUX",
            "NUL",
            "Inbox/NUL.txt",
            "COM1",
            "com9.log",
            "LPT1",
            "Inbox/LPT9",
            "CONIN$",
            "conout$.txt",
            "COM1 .txt",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_superscript_reserved_names(self) -> None:
        for value in (
            "COM¹",
            "COM²",
            "COM³",
            "LPT¹",
            "LPT²",
            "LPT³",
            "lpt³",
            "Inbox/COM².txt",
            "LPT¹ .log",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_invalid_characters(self) -> None:
        for value in (
            "Bad?Folder",
            "Bad*Folder",
            'Bad"Folder',
            "Bad<Folder",
            "Bad>Folder",
            "Bad|Folder",
            "Bad:Folder",
            "Bad\x00Folder",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_trailing_spaces(self) -> None:
        for value in ("Inbox ", "Inbox/Notes ", "Inbox /Notes", "Inbox\t"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_trailing_periods(self) -> None:
        for value in ("Inbox.", "Inbox/Notes.", "Inbox/Notes..."):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_accepts_valid_names_that_resemble_reserved_names(self) -> None:
        for value in (
            "Console",
            "COM10",
            "COM0",
            "LPT0",
            "LPT10",
            "NUL Notes",
            "COM¹ Notes",
            "Inbox/notes-2026",
            "Folder With Spaces",
            "বাংলা",
        ):
            with self.subTest(value=value):
                self.assertEqual(validate_capture_folder(value), value)

    def test_accepts_default_folder(self) -> None:
        self.assertEqual(validate_capture_folder(DEFAULT_CAPTURE_FOLDER), DEFAULT_CAPTURE_FOLDER)


class ValidateConfigTests(unittest.TestCase):
    def test_validates_existing_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            vault.mkdir()
            config = validate_config(str(vault), "Inbox/Quick Captures")
            self.assertEqual(Path(config.vault_path), vault.resolve())
            self.assertEqual(config.capture_folder, "Inbox/Quick Captures")

    def test_rejects_missing_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "not-created"
            with self.assertRaises(ConfigError):
                validate_config(str(missing), DEFAULT_CAPTURE_FOLDER)

    def test_rejects_destination_link_outside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            outside = base / "outside"
            vault.mkdir()
            outside.mkdir()
            link = vault / "Inbox"
            try:
                create_directory_link(link, outside)
                with self.assertRaises(ConfigError):
                    validate_config(str(vault), "Inbox/Captures")
            finally:
                remove_directory_link(link)

    def test_accepts_destination_link_inside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            inside = vault / "Real Inbox"
            vault.mkdir()
            inside.mkdir()
            link = vault / "Inbox"
            try:
                create_directory_link(link, inside)
                config = validate_config(str(vault), "Inbox/Captures")
                self.assertEqual(config.capture_folder, "Inbox/Captures")
            finally:
                remove_directory_link(link)


class ConfigStoreTests(unittest.TestCase):
    def _write_config(self, store: ConfigStore, payload: dict) -> None:
        store.config_dir.mkdir(parents=True, exist_ok=True)
        store.config_file.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def test_saves_and_loads_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            config_dir = base / "settings"
            vault.mkdir()
            store = ConfigStore(config_dir)
            expected = AppConfig(str(vault.resolve()), DEFAULT_CAPTURE_FOLDER)

            store.save(expected)
            loaded = store.load()

            self.assertEqual(loaded, expected)
            self.assertTrue(store.config_file.is_file())
            payload = json.loads(store.config_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)

    def test_returns_none_when_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "settings")
            self.assertIsNone(store.load())

    def test_reports_malformed_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ConfigStore(Path(temp_dir) / "settings")
            store.config_dir.mkdir(parents=True)
            store.config_file.write_text("not json", encoding="utf-8")
            with self.assertRaises(ConfigError):
                store.load()

    def test_rejects_invalid_schema_version_types_and_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            vault.mkdir()
            store = ConfigStore(base / "settings")
            base_payload = {
                "vault_path": str(vault),
                "capture_folder": DEFAULT_CAPTURE_FOLDER,
            }
            missing = object()
            invalid_versions = {
                "missing": missing,
                "boolean true": True,
                "boolean false": False,
                "float 1.0": 1.0,
                "float 1.5": 1.5,
                "string": "1",
                "older": 0,
                "newer": 2,
                "null": None,
            }

            for label, version in invalid_versions.items():
                with self.subTest(version=label):
                    payload = dict(base_payload)
                    if version is not missing:
                        payload["schema_version"] = version
                    self._write_config(store, payload)
                    with self.assertRaises(ConfigError):
                        store.load()

    def test_migrates_legacy_config_without_deleting_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            vault.mkdir()
            new_dir = base / "Obsidrop"
            legacy_dir = base / "VaultDrop"
            legacy_dir.mkdir()
            legacy_file = legacy_dir / "config.json"
            legacy_file.write_text(
                json.dumps({
                    "schema_version": 1,
                    "vault_path": str(vault),
                    "capture_folder": DEFAULT_CAPTURE_FOLDER,
                }),
                encoding="utf-8",
            )

            store = ConfigStore(new_dir, legacy_config_dir=legacy_dir)
            loaded = store.load()

            self.assertEqual(
                loaded,
                AppConfig(str(vault.resolve()), DEFAULT_CAPTURE_FOLDER),
            )
            self.assertTrue(store.config_file.is_file())
            self.assertTrue(legacy_file.is_file())
            self.assertEqual(
                json.loads(store.config_file.read_text(encoding="utf-8"))["vault_path"],
                str(vault.resolve()),
            )

    def test_new_config_takes_precedence_over_legacy_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            first_vault = base / "first"
            second_vault = base / "second"
            first_vault.mkdir()
            second_vault.mkdir()
            new_dir = base / "Obsidrop"
            legacy_dir = base / "VaultDrop"
            store = ConfigStore(new_dir, legacy_config_dir=legacy_dir)
            store.save(AppConfig(str(first_vault), DEFAULT_CAPTURE_FOLDER))

            legacy_dir.mkdir()
            (legacy_dir / "config.json").write_text(
                json.dumps({
                    "schema_version": 1,
                    "vault_path": str(second_vault),
                    "capture_folder": DEFAULT_CAPTURE_FOLDER,
                }),
                encoding="utf-8",
            )

            self.assertEqual(
                store.load(),
                AppConfig(str(first_vault.resolve()), DEFAULT_CAPTURE_FOLDER),
            )


if __name__ == "__main__":
    unittest.main()
