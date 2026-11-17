"""Obsidrop desktop application entry point and main window."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .capture_window import CaptureWindow
from .config import (
    DEFAULT_CAPTURE_FOLDER,
    AppConfig,
    ConfigError,
    ConfigStore,
    validate_config,
)
from .hotkeys import HotkeyError, HotkeyManager, HotkeyNotSupportedError
from .logging_setup import configure_logging
from .markdown_writer import CaptureError, write_capture


class ObsidropApp:
    """Coordinate settings, the capture window, and the global hotkey."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.config_store = ConfigStore()
        self.logger = configure_logging(self.config_store.config_dir)
        self.event_queue: queue.Queue[str] = queue.Queue()
        self.hotkey_manager = HotkeyManager(self.event_queue)
        self.config: AppConfig | None = None
        self.capture_window: CaptureWindow | None = None
        self._hotkey_attempted = False

        self.vault_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=DEFAULT_CAPTURE_FOLDER)
        self.status_var = tk.StringVar(value="Choose your Obsidian vault folder to get started.")
        self.hotkey_var = tk.StringVar(value="Global shortcut: Ctrl + Alt + Space")

        self._build_main_window()
        self._load_existing_config()
        self.root.after(60, self._process_events)

    def _build_main_window(self) -> None:
        self.root.title(f"Obsidrop {__version__}")
        self.root.geometry("640x440")
        self.root.minsize(560, 390)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Obsidrop", font=("Segoe UI", 19, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            outer,
            text="Capture a thought from anywhere and save it directly to your vault.",
            wraplength=580,
        ).grid(row=1, column=0, sticky="w", pady=(3, 18))

        settings = ttk.LabelFrame(outer, text="Storage settings", padding=14)
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(0, weight=1)

        ttk.Label(settings, text="Obsidian vault folder").grid(row=0, column=0, sticky="w")
        vault_row = ttk.Frame(settings)
        vault_row.grid(row=1, column=0, sticky="ew", pady=(5, 12))
        vault_row.columnconfigure(0, weight=1)
        ttk.Entry(vault_row, textvariable=self.vault_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(vault_row, text="Browse…", command=self.browse_vault).grid(
            row=0, column=1, padx=(8, 0)
        )

        ttk.Label(settings, text="Capture folder (relative to the vault)").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(settings, textvariable=self.folder_var).grid(
            row=3, column=0, sticky="ew", pady=(5, 4)
        )
        ttk.Label(
            settings,
            text="Default: Inbox/Quick Captures. Use forward slashes for subfolders.",
            foreground="#666666",
        ).grid(row=4, column=0, sticky="w")

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 10))
        ttk.Button(actions, text="Save settings", command=self.save_settings).pack(side="left")
        ttk.Button(actions, text="Capture now", command=self.show_capture_window).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Open vault folder", command=self.open_vault_folder).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Quit", command=self.quit).pack(side="right")

        status_frame = ttk.LabelFrame(outer, text="Status", padding=12)
        status_frame.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(status_frame, textvariable=self.status_var, wraplength=570).pack(anchor="w")
        ttk.Label(status_frame, textvariable=self.hotkey_var, foreground="#666666").pack(
            anchor="w", pady=(5, 0)
        )

        ttk.Label(
            outer,
            text="Obsidrop writes Markdown files directly. Obsidian does not need to be open.",
            foreground="#666666",
            wraplength=580,
        ).grid(row=5, column=0, sticky="w", pady=(14, 0))

    def _load_existing_config(self) -> None:
        try:
            loaded = self.config_store.load()
        except ConfigError as exc:
            self.logger.warning("Could not load settings: %s", exc)
            self.status_var.set(str(exc))
            return

        if loaded is None:
            return

        self.vault_var.set(loaded.vault_path)
        self.folder_var.set(loaded.capture_folder)
        self.config = loaded
        self.status_var.set("Settings loaded. Starting the global shortcut…")
        self._activate_hotkey()

    def browse_vault(self) -> None:
        selected = filedialog.askdirectory(
            title="Select your Obsidian vault folder",
            initialdir=self.vault_var.get() or str(Path.home()),
            mustexist=True,
        )
        if selected:
            self.vault_var.set(selected)

    def save_settings(self) -> None:
        try:
            checked = validate_config(self.vault_var.get(), self.folder_var.get())
            self.config_store.save(checked)
        except ConfigError as exc:
            self.logger.info("Settings validation/save failed: %s", exc)
            messagebox.showerror("Could not save settings", str(exc), parent=self.root)
            self.status_var.set("Settings were not saved. Check the folder paths.")
            return

        self.config = checked
        self.folder_var.set(checked.capture_folder)
        self.status_var.set("Settings saved. Obsidrop is ready to capture.")
        self.logger.info(
            "Settings saved. Vault=%s Destination=%s",
            checked.vault_path,
            checked.capture_folder,
        )
        self._activate_hotkey()

    def _activate_hotkey(self) -> None:
        if self._hotkey_attempted or self.config is None:
            return

        self._hotkey_attempted = True
        try:
            self.hotkey_manager.start()
            self.hotkey_var.set("Global shortcut active: Ctrl + Alt + Space")
            self.status_var.set("Ready. Press Ctrl + Alt + Space from any application to capture.")
            self.logger.info("Global shortcut registered.")
        except HotkeyNotSupportedError:
            self.hotkey_var.set("Global shortcut: Windows only (manual Capture Now remains available)")
            self.status_var.set("Settings saved. Use Capture Now; the global shortcut requires Windows.")
            self.logger.info("Global hotkey unavailable on this operating system.")
        except HotkeyError as exc:
            self.hotkey_var.set("Global shortcut unavailable; use Capture Now.")
            self.status_var.set(str(exc))
            self.logger.warning("Global shortcut could not be registered: %s", exc)

    def show_capture_window(self) -> None:
        if self.config is None:
            messagebox.showinfo(
                "Set up Obsidrop first",
                "Choose your Obsidian vault folder and save settings before capturing.",
                parent=self.root,
            )
            return

        if self.capture_window is None:
            self.capture_window = CaptureWindow(
                self.root,
                on_save=self._save_capture,
                on_cancel=self._capture_cancelled,
            )
        self.capture_window.show()

    def _save_capture(self, content: str) -> None:
        if self.config is None or self.capture_window is None:
            return

        try:
            saved_path = write_capture(self.config, content)
        except CaptureError as exc:
            self.logger.warning("Capture could not be saved: %s", exc)
            self.capture_window.show_error(str(exc))
            messagebox.showerror("Capture not saved", str(exc), parent=self.capture_window.window)
            return

        self.logger.info("Capture saved: %s", saved_path)
        self.status_var.set(f"Saved: {saved_path}")
        self.capture_window.close_after_save()
        self.capture_window = None

    def _capture_cancelled(self) -> None:
        self.capture_window = None

    def _process_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                if event == "capture":
                    self.show_capture_window()
                elif event.startswith("hotkey_error:"):
                    message = event.partition(":")[2]
                    self.hotkey_var.set("Global shortcut unavailable; use Capture Now.")
                    self.status_var.set(message)
                    self.logger.warning(message)
        except queue.Empty:
            pass

        try:
            self.root.after(60, self._process_events)
        except tk.TclError:
            # The root window is already shutting down.
            return

    def open_vault_folder(self) -> None:
        if self.config is None:
            messagebox.showinfo("Vault not configured", "Save your vault settings first.", parent=self.root)
            return

        vault = Path(self.config.vault_path)
        try:
            if os.name == "nt":
                os.startfile(str(vault))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(vault)])
            else:
                subprocess.Popen(["xdg-open", str(vault)])
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.exception("Could not open vault folder")
            messagebox.showerror("Could not open folder", str(exc), parent=self.root)

    def quit(self) -> None:
        self.logger.info("Obsidrop is shutting down.")
        try:
            self.hotkey_manager.stop()
        finally:
            self.root.destroy()


def main() -> None:
    """Create and run the Tkinter application."""

    root = tk.Tk()
    try:
        ObsidropApp(root)
        root.mainloop()
    except Exception:
        logging.getLogger("obsidrop").exception("Application terminated unexpectedly.")
        raise


if __name__ == "__main__":
    main()
