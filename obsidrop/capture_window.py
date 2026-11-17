"""Small floating Tkinter window used for quick captures."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class CaptureWindow:
    """A reusable, focused multiline capture window."""

    def __init__(
        self,
        root: tk.Tk,
        on_save: Callable[[str], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self.root = root
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.window: tk.Toplevel | None = None
        self.text: tk.Text | None = None
        self.error_var: tk.StringVar | None = None

    @property
    def is_open(self) -> bool:
        return self.window is not None and self.window.winfo_exists()

    def show(self) -> None:
        """Create or focus the capture window without discarding draft text."""

        if self.is_open:
            assert self.window is not None
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            if self.text is not None:
                self.text.focus_set()
            return

        window = tk.Toplevel(self.root)
        self.window = window
        window.title("Obsidrop — Quick Capture")
        window.geometry("560x320")
        window.minsize(420, 240)
        window.resizable(True, True)
        # Do not mark this as transient: the main window may be minimized when
        # the global shortcut is pressed, and the capture window must still appear.
        window.protocol("WM_DELETE_WINDOW", self.cancel)
        window.bind("<Escape>", lambda _event: self.cancel())
        window.bind("<Control-Return>", self._save_shortcut)
        window.bind("<Control-KP_Enter>", self._save_shortcut)

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Quick capture", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        text = tk.Text(
            frame,
            wrap="word",
            undo=True,
            padx=9,
            pady=8,
            font=("Segoe UI", 10),
            borderwidth=1,
            relief="solid",
        )
        text.grid(row=1, column=0, sticky="nsew")
        self.text = text

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)

        self.error_var = tk.StringVar(value="Ctrl + Enter to save · Esc to cancel")
        ttk.Label(frame, textvariable=self.error_var).grid(
            row=2, column=0, sticky="w", pady=(8, 8)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save capture", command=self.save).pack(side="right")

        self._center_window(window)
        window.after(80, self._focus_and_raise)

    def _center_window(self, window: tk.Toplevel) -> None:
        self.root.update_idletasks()
        width, height = 560, 320
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 3)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _focus_and_raise(self) -> None:
        if not self.is_open:
            return
        assert self.window is not None
        self.window.attributes("-topmost", True)
        self.window.lift()
        self.window.focus_force()
        if self.text is not None:
            self.text.focus_set()
        # Keep topmost only long enough to bring the window forward.
        self.window.after(350, self._remove_topmost)

    def _remove_topmost(self) -> None:
        if self.is_open and self.window is not None:
            try:
                self.window.attributes("-topmost", False)
            except tk.TclError:
                pass

    def _save_shortcut(self, _event: tk.Event) -> str:
        self.save()
        return "break"

    def save(self) -> None:
        if self.text is None or not self.is_open:
            return
        content = self.text.get("1.0", "end-1c")
        self.on_save(content)

    def show_error(self, message: str) -> None:
        if self.error_var is not None:
            self.error_var.set(message)

    def close_after_save(self) -> None:
        if self.is_open and self.window is not None:
            self.window.destroy()
        self.window = None
        self.text = None
        self.error_var = None

    def cancel(self) -> None:
        self.close_after_save()
        self.on_cancel()
