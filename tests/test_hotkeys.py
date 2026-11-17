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
        self.queue_initialized = threading.Event()
        self.post_failed = threading.Event()
        self.post_should_fail = False
        self.peek_observer = None
        self.user32 = mock.MagicMock()
        self.kernel32 = mock.MagicMock()
        self.user32.RegisterHotKey.side_effect = list(register_results)
        self.user32.GetMessageW.side_effect = get_message
        self.user32.PeekMessageW.side_effect = self._peek_message
        self.user32.PostThreadMessageW.side_effect = self._post_thread_message
        self.user32.UnregisterHotKey.return_value = 1
        self.kernel32.GetCurrentThreadId.return_value = 4242

    def _peek_message(self, _message, _hwnd, _minimum, _maximum, _remove) -> int:
        self.queue_initialized.set()
        if self.peek_observer is not None:
            self.peek_observer()
        return 0

    def _post_thread_message(self, _thread_id, message, _wparam, _lparam) -> int:
        if message != hotkeys.WM_QUIT:
            return 1
        if self.post_should_fail or not self.queue_initialized.is_set():
            self.post_failed.set()
            return 0
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
    def make_manager(self, fake: FakeWin32, last_error: int = 1409) -> hotkeys.HotkeyManager:
        event_queue: queue.Queue[str] = queue.Queue()
        manager = hotkeys.HotkeyManager(event_queue)

        for patcher in (
            mock.patch.object(hotkeys.os, "name", "nt"),
            mock.patch.object(ctypes, "WinDLL", side_effect=fake.load, create=True),
            mock.patch.object(ctypes, "get_last_error", return_value=last_error, create=True),
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

    def test_message_queue_is_initialized_before_successful_startup(self) -> None:
        fake = FakeWin32([1], lambda *_args: 0)
        fake.user32.GetMessageW.side_effect = blocking_get_message(fake)
        manager = self.make_manager(fake)
        ready_states: list[bool] = []
        fake.peek_observer = lambda: ready_states.append(manager._ready.is_set())

        manager.start(timeout=1.0)

        self.assertEqual(ready_states, [False])
        self.assertTrue(fake.queue_initialized.is_set())
        self.assertEqual(fake.user32.PeekMessageW.call_count, 1)
        self.assertTrue(manager.is_running)

        manager.stop()
        self.assertFalse(manager._thread.is_alive())

    def test_stop_immediately_after_startup_terminates_worker(self) -> None:
        fake = FakeWin32([1], lambda *_args: 0)
        fake.user32.GetMessageW.side_effect = blocking_get_message(fake)
        manager = self.make_manager(fake)

        manager.start(timeout=1.0)
        worker = manager._thread
        manager.stop(timeout=1.0)

        self.assertIsNotNone(worker)
        self.assertFalse(worker.is_alive())
        self.assertGreaterEqual(fake.user32.PostThreadMessageW.call_count, 1)
        self.assertTrue(manager.event_queue.empty())

    def test_stop_during_startup_does_not_leave_worker_blocked(self) -> None:
        registration_started = threading.Event()
        release_registration = threading.Event()
        fake = FakeWin32([1], lambda *_args: 0)
        fake.post_should_fail = True

        def register(*_args) -> int:
            registration_started.set()
            release_registration.wait(2.0)
            return 1

        fake.user32.RegisterHotKey.side_effect = register
        manager = self.make_manager(fake)
        start_errors: list[Exception] = []

        def run_start() -> None:
            try:
                manager.start(timeout=2.0)
            except Exception as exc:
                start_errors.append(exc)

        starter = threading.Thread(target=run_start, daemon=True)
        starter.start()
        self.assertTrue(registration_started.wait(1.0))

        stopper = threading.Thread(target=manager.stop, kwargs={"timeout": 1.0})
        stopper.start()
        try:
            self.assertTrue(fake.post_failed.wait(1.0))
        finally:
            release_registration.set()

        stopper.join(2.0)
        starter.join(2.0)

        self.assertFalse(stopper.is_alive())
        self.assertFalse(starter.is_alive())
        self.assertFalse(manager._thread.is_alive())
        self.assertEqual(fake.user32.GetMessageW.call_count, 0)
        self.assertTrue(manager.event_queue.empty())
        self.assertEqual(len(start_errors), 1)
        self.assertIsInstance(start_errors[0], hotkeys.HotkeyError)
        self.assertIn("interrupted", str(start_errors[0]))

    def test_failed_shutdown_post_is_reported(self) -> None:
        fake = FakeWin32([1], lambda *_args: 0)
        fake.user32.GetMessageW.side_effect = blocking_get_message(fake)
        fake.post_should_fail = True
        manager = self.make_manager(fake, last_error=5)

        manager.start(timeout=1.0)
        worker = manager._thread
        manager.stop(timeout=0.05)

        self.assertIsNotNone(worker)
        self.assertTrue(worker.is_alive())
        event = manager.event_queue.get(timeout=1.0)
        self.assertEqual(
            event,
            "hotkey_error:Windows did not stop the hotkey worker cleanly "
            "(PostThreadMessageW failed with Windows error 5).",
        )
        self.assertTrue(manager.event_queue.empty())

        fake.quit_requested.set()
        worker.join(2.0)
        self.assertFalse(worker.is_alive())

    def test_concurrent_runtime_errors_are_reported_once(self) -> None:
        event_queue: queue.Queue[str] = queue.Queue()
        manager = hotkeys.HotkeyManager(event_queue)
        thread_count = 8
        barrier = threading.Barrier(thread_count)

        def report() -> None:
            barrier.wait(timeout=2.0)
            manager._report_runtime_error("concurrent failure")

        threads = [threading.Thread(target=report) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(2.0)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(event_queue.qsize(), 1)
        self.assertEqual(
            event_queue.get_nowait(),
            "hotkey_error:concurrent failure",
        )

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
