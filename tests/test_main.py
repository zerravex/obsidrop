from __future__ import annotations

import unittest
from unittest import mock

from obsidrop.config import AppConfig
from obsidrop.hotkeys import HotkeyError, HotkeyNotSupportedError

try:
    import tkinter  # noqa: F401
except ImportError:  # Tkinter is optional on minimal Linux CI images.
    ObsidropApp = None
else:
    from obsidrop.main import ObsidropApp


@unittest.skipIf(ObsidropApp is None, "Tkinter is unavailable on this system.")
class ActivateHotkeyTests(unittest.TestCase):
    def make_app(self):
        app = ObsidropApp.__new__(ObsidropApp)
        app.config = object()
        app.hotkey_manager = mock.MagicMock()
        app.hotkey_manager.is_running = False
        app.hotkey_var = mock.Mock()
        app.status_var = mock.Mock()
        app.logger = mock.Mock()
        app._hotkey_unsupported = False
        return app

    def test_does_nothing_without_configuration(self) -> None:
        app = self.make_app()
        app.config = None

        app._activate_hotkey()

        app.hotkey_manager.start.assert_not_called()

    def test_does_not_register_an_already_running_hotkey(self) -> None:
        app = self.make_app()
        app.hotkey_manager.is_running = True

        app._activate_hotkey()

        app.hotkey_manager.start.assert_not_called()

    def test_retries_after_a_failed_registration(self) -> None:
        app = self.make_app()
        app.hotkey_manager.start.side_effect = [HotkeyError("shortcut busy"), None]

        app._activate_hotkey()
        app._activate_hotkey()

        self.assertEqual(app.hotkey_manager.start.call_count, 2)
        app.status_var.set.assert_called_with(
            "Ready. Press Ctrl + Alt + Space from any application to capture."
        )

    def test_non_windows_platform_is_not_retried_repeatedly(self) -> None:
        app = self.make_app()
        app.hotkey_manager.start.side_effect = HotkeyNotSupportedError("Windows only")

        app._activate_hotkey()
        app._activate_hotkey()

        self.assertEqual(app.hotkey_manager.start.call_count, 1)
        self.assertTrue(app._hotkey_unsupported)


@unittest.skipIf(ObsidropApp is None, "Tkinter is unavailable on this system.")
class SaveSettingsTests(unittest.TestCase):
    def make_app(self):
        app = ObsidropApp.__new__(ObsidropApp)
        app.config_store = mock.Mock()
        app.config_store.config_dir = object()
        app.vault_var = mock.Mock()
        app.vault_var.get.return_value = "vault"
        app.folder_var = mock.Mock()
        app.folder_var.get.return_value = "Inbox"
        app.status_var = mock.Mock()
        app.logger = mock.Mock()
        app._activate_hotkey = mock.Mock()
        return app

    def test_save_settings_retries_logging_initialization(self) -> None:
        app = self.make_app()
        checked = AppConfig("vault", "Inbox")
        replacement_logger = mock.Mock()

        with (
            mock.patch("obsidrop.main.configure_logging", return_value=replacement_logger) as configure,
            mock.patch("obsidrop.main.validate_config", return_value=checked),
        ):
            app.save_settings()

        configure.assert_called_once_with(app.config_store.config_dir)
        self.assertIs(app.logger, replacement_logger)
        app.config_store.save.assert_called_once_with(checked)
        app._activate_hotkey.assert_called_once()


if __name__ == "__main__":
    unittest.main()
