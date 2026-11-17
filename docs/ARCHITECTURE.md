# Architecture — Obsidrop v0.0.1

## 1. Architecture overview

Obsidrop is a single-process desktop application. Tkinter owns the user interface. A small Win32 message-pump thread receives the global hotkey. A thread-safe queue transfers events to the Tkinter main thread. The capture writer validates the configured vault path and writes Markdown directly to disk.

```text
                Windows desktop
                       |
              Ctrl + Alt + Space
                       |
                       v
              Win32 RegisterHotKey
                       |
                       v
              Hotkey message thread
                       |
                queue.Queue[str]
                       |
                       v
              Tkinter main thread
                 /           \
                v             v
          Main window    Capture window
                              |
                              v
                       Markdown writer
                              |
                       Path validation
                              |
                              v
                    Configured vault folder
                              |
                              v
                         note.md
```

Obsidian is not part of the runtime path. It may notice the new Markdown file through its normal vault filesystem watcher when it is open, but Obsidrop does not call Obsidian APIs in this release.

## 2. Module responsibilities

| Module | Responsibility | Must not do |
|---|---|---|
| `app.py` | Thin script entry point | Contain application logic |
| `obsidrop/main.py` | Construct the main window, coordinate components, poll events, manage shutdown | Implement low-level path rules or Win32 message structures |
| `obsidrop/config.py` | Configuration paths, JSON persistence, vault and destination validation | Create Markdown notes or manage UI widgets |
| `obsidrop/hotkeys.py` | Register and unregister the Windows global shortcut; deliver event tokens | Call Tkinter methods |
| `obsidrop/capture_window.py` | Build and manage the floating capture window | Write files directly |
| `obsidrop/markdown_writer.py` | Render and safely create Markdown files | Read UI state or show dialogs |
| `obsidrop/logging_setup.py` | Configure a rotating log | Log captured note bodies |

## 3. Configuration

On Windows, settings live at `%APPDATA%\Obsidrop\config.json`. The file contains:

```json
{
  "schema_version": 1,
  "vault_path": "C:\\Users\\Example\\Documents\\My Vault",
  "capture_folder": "Inbox/Quick Captures"
}
```

The configuration directory is outside the vault. The file is written to a temporary file in the same directory, flushed, and atomically replaced into place.

## 4. Capture data flow

1. A hotkey event or manual button action reaches the Tkinter thread.
2. The capture window is created or raised. Existing draft text is preserved if the window is already open.
3. The user enters text and saves.
4. The writer rejects non-text or whitespace-only content.
5. The writer revalidates the vault and relative folder.
6. The destination directory is created if needed.
7. The resolved destination is checked again to prevent symlink escapes.
8. The writer builds a timestamped filename.
9. The file is opened with exclusive-create mode (`x`). If it already exists, a numeric suffix is tried.
10. The writer writes UTF-8 Markdown and flushes the file.
11. Only after a successful write does the UI close the capture window and report the saved path.

## 5. Threading model

Tkinter is not thread-safe. All widget operations stay on the main thread.

`RegisterHotKey` with a null window handle associates the hotkey with the thread that registered it. Therefore `hotkeys.py` owns a dedicated worker thread that registers the shortcut and runs a Win32 message loop. When `WM_HOTKEY` arrives, that thread places the string token `capture` in a `queue.Queue`. The GUI checks the queue periodically using `root.after` and opens the capture window itself.

On shutdown, the GUI posts `WM_QUIT` to the hotkey worker. The worker exits its message loop and unregisters the shortcut in its `finally` block.

## 6. Filesystem safety

- The selected vault root is resolved and must exist as a directory.
- The capture folder is normalized as a relative path.
- Absolute paths, drive-qualified paths, `..`, invalid Windows characters, reserved device names, and trailing spaces/periods are rejected.
- The destination is resolved and checked to remain under the vault.
- The writer repeats the containment check after creating the directory, covering pre-existing symlink components.
- The final note is opened exclusively. Existing notes are never intentionally replaced.

This is a practical local-desktop safety boundary, not a hardened security sandbox against a malicious process running as the same Windows user. A same-user process could still change filesystem entries between checks.

## 7. Error behavior

- Invalid configuration: show a recoverable message in the main window or dialog.
- Hotkey conflict: explain that the shortcut is unavailable and keep the manual button enabled.
- Empty text: reject save and keep the capture window open.
- File permission/disk error: show an error and keep the editor open.
- Unexpected application errors: log diagnostic details without logging captured note bodies.

## 8. Future extension points

Later versions may add a system tray, clipboard capture, explicit selection capture, browser extension, attachment handling, configurable routes, and an Obsidian companion plugin. These should integrate through small, documented interfaces. They should not make the core Markdown writer depend on Obsidian being open or on a network service.
