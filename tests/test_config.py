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


class ValidateCaptureFolderTests(unittest.TestCase):
    def test_normalizes_backslashes(self) -> None:
        self.assertEqual(
            validate_capture_folder(r"Inbox\Quick Captures"),
            "Inbox/Quick Captures",
        )

    def test_rejects_empty_folder(self) -> None:
        with self.assertRaises(ConfigError):
            validate_capture_folder("  ")

    def test_rejects_parent_traversal(self) -> None:
        for value in ("../outside", "Inbox/../../outside", r"Inbox\..\outside"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_absolute_and_drive_paths(self) -> None:
        for value in ("/outside", r"C:\outside", r"\\server\share"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_rejects_windows_reserved_names_and_characters(self) -> None:
        for value in ("CON", "Inbox/NUL.txt", "Bad?Folder", "Trailing."):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_capture_folder(value)

    def test_accepts_default_folder(self) -> None:
        self.assertEqual(validate_capture_folder(DEFAULT_CAPTURE_FOLDER), DEFAULT_CAPTURE_FOLDER)


class ValidateConfigTests(unittest.TestCase):
    def test_validates_existing_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = validate_config(temp_dir, "Inbox/Quick Captures")
            self.assertEqual(Path(config.vault_path), Path(temp_dir).resolve())
            self.assertEqual(config.capture_folder, "Inbox/Quick Captures")

    def test_rejects_missing_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "not-created"
            with self.assertRaises(ConfigError):
                validate_config(str(missing), DEFAULT_CAPTURE_FOLDER)

    def test_rejects_destination_symlink_outside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            outside = base / "outside"
            vault.mkdir()
            outside.mkdir()
            link = vault / "Inbox"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlinks are unavailable on this system.")
            with self.assertRaises(ConfigError):
                validate_config(str(vault), "Inbox/Captures")


class ConfigStoreTests(unittest.TestCase):
    def test_saves_and_loads_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            vault = base / "vault"
            config_dir = base / "settings"
            vault.mkdir()
            store = ConfigStore(config_dir)
            expected = AppConfig(str(vault), DEFAULT_CAPTURE_FOLDER)

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

            self.assertEqual(loaded, AppConfig(str(vault.resolve()), DEFAULT_CAPTURE_FOLDER))
            self.assertTrue(store.config_file.is_file())
            self.assertTrue(legacy_file.is_file())
            self.assertEqual(json.loads(store.config_file.read_text(encoding="utf-8"))["vault_path"], str(vault.resolve()))

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

            self.assertEqual(store.load(), AppConfig(str(first_vault.resolve()), DEFAULT_CAPTURE_FOLDER))


if __name__ == "__main__":
    unittest.main()
