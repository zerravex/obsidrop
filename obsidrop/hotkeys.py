"""Windows global-hotkey registration using only ctypes and the standard library."""

from __future__ import annotations

import ctypes
import os
import queue
import threading
from ctypes import wintypes


class HotkeyError(RuntimeError):
    """Raised when the global shortcut cannot be registered or managed."""


class HotkeyNotSupportedError(HotkeyError):
    """Raised when the application is not running on Windows."""


# Windows message and modifier constants.
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_SPACE = 0x20
HOTKEY_ID = 0x5644  # 'VD'


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    """Native Windows MSG structure, including its reserved lPrivate field."""

    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
        ("lPrivate", wintypes.DWORD),
    ]


class HotkeyManager:
    """Register Ctrl+Alt+Space on a dedicated Windows message-pump thread.

    The worker thread only places a small event token into a thread-safe queue.
    The Tkinter main thread consumes that token and performs all UI operations.
    """

    def __init__(self, event_queue: queue.Queue[str]) -> None:
        self.event_queue = event_queue
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._thread_id: int | None = None
        self._startup_error: str | None = None
        self._user32 = None
        self._registered = False
        self._stop_requested = False
        self._runtime_error_reported = False

    @property
    def is_running(self) -> bool:
        return (
            self._thread is not None
            and self._thread.is_alive()
            and self._registered
            and self._startup_error is None
        )

    def _report_runtime_error(self, message: str) -> None:
        """Send at most one runtime failure event for the current worker."""

        if self._runtime_error_reported:
            return
        self._runtime_error_reported = True
        self.event_queue.put(f"hotkey_error:{message}")

    def start(self, timeout: float = 3.0) -> None:
        """Start the hotkey worker and wait until registration succeeds or fails."""

        if os.name != "nt":
            raise HotkeyNotSupportedError("The global keyboard shortcut is supported on Windows only.")

        if self._thread is not None and self._thread.is_alive():
            if self.is_running:
                return
            # A worker that has just failed may still be unwinding. Do not start
            # a second listener while the first one may still own the shortcut.
            self._thread.join(timeout)
            if self._thread.is_alive():
                raise HotkeyError("The previous global shortcut listener is still shutting down.")

        self._ready = threading.Event()
        self._startup_error = None
        self._registered = False
        self._stop_requested = False
        self._runtime_error_reported = False
        self._thread = threading.Thread(
            target=self._message_pump,
            name="ObsidropHotkey",
            daemon=True,
        )
        self._thread.start()

        if not self._ready.wait(timeout):
            self.stop()
            raise HotkeyError("Windows did not respond while registering the global shortcut.")

        if self._startup_error:
            raise HotkeyError(self._startup_error)

    def _message_pump(self) -> None:
        """Register the hotkey and process messages on this worker thread."""

        registered = False
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._user32 = user32

            user32.RegisterHotKey.argtypes = [
                wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT
            ]
            user32.RegisterHotKey.restype = wintypes.BOOL
            user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.UnregisterHotKey.restype = wintypes.BOOL
            user32.GetMessageW.argtypes = [
                ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
            ]
            user32.GetMessageW.restype = ctypes.c_int
            user32.PostThreadMessageW.argtypes = [
                wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
            ]
            user32.PostThreadMessageW.restype = wintypes.BOOL
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD

            self._thread_id = int(kernel32.GetCurrentThreadId())
            modifiers = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
            registered_hotkey = user32.RegisterHotKey(None, HOTKEY_ID, modifiers, VK_SPACE)
            if not registered_hotkey:
                error_code = ctypes.get_last_error()
                self._startup_error = (
                    f"Could not register Ctrl+Alt+Space (Windows error {error_code}). "
                    "Another application may already be using this shortcut. "
                    "You can still use the Capture Now button."
                )
                return

            registered = True
            self._registered = True
            self._ready.set()

            message = MSG()
            while not self._stop_requested:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    error_code = ctypes.get_last_error()
                    self._report_runtime_error(
                        f"Windows message loop failed (error {error_code})."
                    )
                    break
                if result == 0:  # WM_QUIT
                    if not self._stop_requested:
                        self._report_runtime_error(
                            "The global shortcut listener stopped unexpectedly."
                        )
                    break
                if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                    self.event_queue.put("capture")
        except Exception as exc:  # Keep native API failures visible to the main UI.
            if registered:
                self._report_runtime_error(
                    f"Global shortcut worker stopped unexpectedly: {exc}"
                )
            else:
                self._startup_error = f"Global shortcut initialization failed: {exc}"
        finally:
            self._registered = False
            self._ready.set()
            if self._thread_id is not None and self._user32 is not None:
                try:
                    self._user32.UnregisterHotKey(None, HOTKEY_ID)
                except Exception:
                    pass
            self._thread_id = None

    def stop(self, timeout: float = 2.0) -> None:
        """Stop the message-pump thread and release the global shortcut."""

        thread = self._thread
        thread_id = self._thread_id
        if thread is None or not thread.is_alive():
            return

        self._stop_requested = True
        if thread_id is not None and self._user32 is not None:
            try:
                self._user32.PostThreadMessageW(
                    thread_id, WM_QUIT, 0, 0
                )
            except Exception:
                pass
        thread.join(timeout)
        if thread.is_alive():
            # A daemon worker prevents shutdown from hanging, but report the issue.
            self._report_runtime_error("Windows did not stop the hotkey worker cleanly.")
