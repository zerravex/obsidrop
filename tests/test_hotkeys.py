from __future__ import annotations

import ctypes
import queue
import threading
import unittest
from unittest import mock

from obsidrop import hotkeys


class FakeWin32:
    """A small fake for the Win32 calls used by HotkeyManager."""

    def __init__(self, register_results, get_message) -> None:
        self.quit_requested = threading.Event()
        self.user32 = mock.MagicMock()
        self.kernel32 = mock.MagicMock()
        self.user32.RegisterHotKey.side_effect = list(register_results)
        self.user32.GetMessageW.side_effect = get_message
        self.user32.PostThreadMessageW.side_effect = self._post_thread_message
        self.user32.UnregisterHotKey.return_value = 1
        self.kernel32.GetCurrentThreadId.return_value = 4242

    def _post_thread_message(self, _thread_id, message, _wparam, _lparam) -> int:
        if message == hotkeys.WM_QUIT:
            self.quit_requested.set()
        return 1

    def load(self, name: str, use_last_error: bool = True):
        return {"user32": self.user32, "kernel32": self.kernel32}[name]


def blocking_get_message(fake: FakeWin32):
    def get_message(_message, _hwnd, _minimum, _maximum) -> int:
        fake.quit_requested.wait(5)
        return 0

    return get_message


class HotkeyManagerTests(unittest.TestCase):
    def make_manager(self, fake: FakeWin32) -> hotkeys.HotkeyManager:
        event_queue: queue.Queue[str] = queue.Queue()
        manager = hotkeys.HotkeyManager(event_queue)

        for patcher in (
            mock.patch.object(hotkeys.os, "name", "nt"),
            mock.patch.object(ctypes, "WinDLL", side_effect=fake.load, create=True),
            mock.patch.object(ctypes, "get_last_error", return_value=1409, create=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

        self.addCleanup(manager.stop)
        return manager

    def test_failed_startup_registration_can_be_retried(self) -> None:
        fake = FakeWin32([0, 1], lambda *_args: 0)
        fake.user32.GetMessageW.side_effect = blocking_get_message(fake)
        manager = self.make_manager(fake)

        with self.assertRaises(hotkeys.HotkeyError):
            manager.start(timeout=1.0)
        self.assertFalse(manager.is_running)
        self.assertTrue(manager.event_queue.empty())

        manager.start(timeout=1.0)
        self.assertTrue(manager.is_running)
        self.assertEqual(fake.user32.RegisterHotKey.call_count, 2)

        manager.stop()
        self.assertTrue(manager.event_queue.empty())

    def test_repeated_start_does_not_duplicate_listener(self) -> None:
        fake = FakeWin32([1], lambda *_args: 0)
        fake.user32.GetMessageW.side_effect = blocking_get_message(fake)
        manager = self.make_manager(fake)

        manager.start(timeout=1.0)
        first_thread = manager._thread
        manager.start(timeout=1.0)

        self.assertIs(manager._thread, first_thread)
        self.assertEqual(fake.user32.RegisterHotKey.call_count, 1)
        self.assertTrue(manager.event_queue.empty())

        manager.stop()
        self.assertTrue(manager.event_queue.empty())

    def test_runtime_message_loop_error_is_reported_once(self) -> None:
        fake = FakeWin32([1], lambda *_args: -1)
        manager = self.make_manager(fake)

        manager.start(timeout=1.0)
        self.assertIsNotNone(manager._thread)
        manager._thread.join(2.0)

        self.assertFalse(manager._thread.is_alive())
        self.assertFalse(manager.is_running)
        event = manager.event_queue.get(timeout=1.0)
        self.assertEqual(
            event,
            "hotkey_error:Windows message loop failed (error 1409).",
        )
        self.assertTrue(manager.event_queue.empty())

        manager.stop()
        self.assertTrue(manager.event_queue.empty())

    def test_unexpected_worker_exception_is_reported(self) -> None:
        fake = FakeWin32([1], lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")))
        manager = self.make_manager(fake)

        manager.start(timeout=1.0)
        self.assertIsNotNone(manager._thread)
        manager._thread.join(2.0)

        self.assertFalse(manager._thread.is_alive())
        self.assertFalse(manager.is_running)
        event = manager.event_queue.get(timeout=1.0)
        self.assertIn("hotkey_error:", event)
        self.assertIn("boom", event)
        self.assertTrue(manager.event_queue.empty())

    def test_unexpected_message_loop_exit_is_reported(self) -> None:
        fake = FakeWin32([1], lambda *_args: 0)
        manager = self.make_manager(fake)

        manager.start(timeout=1.0)
        self.assertIsNotNone(manager._thread)
        manager._thread.join(2.0)

        self.assertFalse(manager.is_running)
        event = manager.event_queue.get(timeout=1.0)
        self.assertIn("stopped unexpectedly", event)

    def test_registration_failure_is_not_reported_as_runtime_error(self) -> None:
        fake = FakeWin32([0], lambda *_args: 0)
        manager = self.make_manager(fake)

        with self.assertRaises(hotkeys.HotkeyError):
            manager.start(timeout=1.0)

        self.assertIsNotNone(manager._thread)
        manager._thread.join(2.0)
        self.assertTrue(manager.event_queue.empty())

    def test_non_windows_platform_is_reported(self) -> None:
        event_queue: queue.Queue[str] = queue.Queue()
        manager = hotkeys.HotkeyManager(event_queue)

        with mock.patch.object(hotkeys.os, "name", "posix"):
            with self.assertRaises(hotkeys.HotkeyNotSupportedError):
                manager.start(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
