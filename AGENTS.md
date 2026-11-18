# Obsidrop — Persistent Instructions for AI Coding Agents

> Read this file before changing anything. It is the repository's operating manual for coding agents, including smaller models with limited context. Follow it unless the user explicitly requests a conflicting change.

## 1. Project identity and purpose

**Obsidrop** is a small, local-first desktop utility for capturing a thought from anywhere on a Windows desktop and saving it as a Markdown file inside a folder selected by the user, usually an Obsidian vault.

The intended workflow is:
1. Start Obsidrop.
2. Select an existing vault folder and a destination folder inside it.
3. Press the global shortcut `Ctrl + Alt + Space`, or click **Capture now**.
4. Type or paste text into a small floating window.
5. Press `Ctrl + Enter` or click **Save capture**.
6. Obsidrop creates a new timestamped `.md` file in the selected destination.

**Obsidian does not need to be open, installed, or running for the core workflow.** An Obsidian vault is an ordinary folder containing Markdown files and optional Obsidian metadata. Obsidrop writes a regular Markdown file directly to that folder.

Product goals:
- Minimize the time and effort between having a thought and preserving it.
- Be fast, lightweight, predictable, and understandable.
- Keep notes on the user's own computer in portable Markdown.
- Avoid unnecessary services, dependencies, accounts, network access, and AI in the critical capture path.

Current release: `0.0.1`, an early source-code prototype. Primary target: Windows 10/11. Minimum Python: 3.10. GUI: Tkinter/ttk. Runtime dependencies: Python standard library only. Do not describe this as a polished or fully Windows-verified release; the native hotkey and real GUI behavior require manual Windows testing.

## 2. Current scope

### Implemented in v0.0.1
- Main settings window and first-run vault selection.
- Configurable vault-relative destination folder; default `Inbox/Quick Captures`.
- JSON configuration stored outside the vault.
- Floating multiline capture window.
- Global Windows shortcut `Ctrl + Alt + Space` and manual **Capture now** fallback.
- `Ctrl + Enter` saves; `Esc` cancels.
- Timestamped Markdown output with YAML frontmatter.
- UTF-8 writing, including Bangla and other Unicode text.
- Collision-safe file creation; existing files are not intentionally overwritten.
- Path validation and checks against destination symlinks escaping the vault.
- Application logging outside the vault.
- Standard-library automated tests.

### Explicitly out of scope unless the user requests a scope change
- Clipboard monitoring or automatic clipboard capture.
- Reading selected text from arbitrary applications.
- Inspecting foreground-window titles or contents.
- Screenshots, images, or file attachments.
- System tray, run-at-login, or background service.
- Configurable hotkeys.
- Appending to daily notes or editing existing notes.
- Browser extension or Obsidian companion plugin.
- AI classification, AI API calls, cloud sync, accounts, telemetry, or analytics.
- Database, installer, or packaged executable.

These may appear in `docs/ROADMAP.md`. A roadmap item is a future possibility, **not a current requirement or permission to implement it**.

## 3. Repository map

```text
Obsidrop/
├── app.py                       # Simple launcher; calls obsidrop.main.main()
├── run_obsidrop.bat            # Windows launcher; creates .venv if needed
├── requirements.txt             # States that no third-party packages are needed
├── pyproject.toml               # Project metadata and Python minimum version
├── .gitignore                   # Excludes local/generated files
├── .github/
│   └── workflows/
│       └── tests.yml            # CI: Windows/Linux, Python 3.14 and 3.15
├── AGENTS.md                    # This file: AI coding-agent instructions
├── README.md                    # User-facing overview and instructions
├── CHANGELOG.md                 # Version history
├── obsidrop/                   # Application source package
│   ├── __init__.py              # Package version
│   ├── __main__.py              # Enables `python -m obsidrop`
│   ├── main.py                  # App coordinator, main window, settings, events, shutdown
│   ├── config.py                # AppConfig, JSON persistence, path validation
│   ├── hotkeys.py               # Win32 RegisterHotKey wrapper and worker message loop
│   ├── capture_window.py        # Floating capture UI and keyboard shortcuts
│   ├── markdown_writer.py       # Markdown rendering and safe file creation
│   └── logging_setup.py         # Log configuration and rotation
├── tests/
│   ├── __init__.py
│   ├── support.py               # Shared filesystem test helpers
│   ├── test_config.py           # Configuration and destination-path tests
│   ├── test_hotkeys.py          # Mocked Win32 hotkey worker tests
│   ├── test_logging_setup.py    # Logging initialization and recovery tests
│   ├── test_main.py             # Hotkey activation retry tests
│   └── test_markdown_writer.py  # Markdown and filesystem-write tests
└── docs/
    ├── PRODUCT_SPEC.md          # Requirements and acceptance criteria
    ├── ARCHITECTURE.md          # Component boundaries and technical design
    ├── DEVELOPMENT.md           # Development and AI-assisted workflow
    ├── TEST_PLAN.md             # Automated and manual verification plan
    ├── PRIVACY_AND_DATA.md      # Data flows, storage, privacy boundaries
    └── ROADMAP.md               # Potential future releases
```

### Module responsibilities

| Module | Owns | Does not own |
|---|---|---|
| `main.py` | App lifecycle, main window, event coordination, settings workflow, user-facing status | Win32 message-loop implementation or Markdown formatting |
| `config.py` | `AppConfig`, JSON persistence, configuration and path validation | Tkinter widgets or note-file creation |
| `hotkeys.py` | Native Windows hotkey registration, message pump, queue events, release | Any Tkinter widget operation |
| `capture_window.py` | Capture-window widgets, draft text, Save/Cancel callbacks | Filesystem destination logic |
| `markdown_writer.py` | Config revalidation, Markdown rendering, unique file creation | GUI, dialogs, hotkey registration |
| `logging_setup.py` | Rotating application logs | Note bodies or business logic |

Keep these boundaries. If a feature appears to require crossing them, explain why and propose the smallest design that preserves separation.

## 4. Source-of-truth documents

Read relevant documents before implementation. Priority:
1. `docs/PRODUCT_SPEC.md` — what v0.0.1 must do.
2. `docs/ARCHITECTURE.md` — how the implementation is structured.
3. `docs/TEST_PLAN.md` — how behavior must be verified.
4. `docs/PRIVACY_AND_DATA.md` — data-handling promises.
5. `docs/ROADMAP.md` — future possibilities only.
6. `README.md` — user-facing setup and use.
7. `CHANGELOG.md` — recorded release changes.

If documents and code disagree, do not silently guess. Report the discrepancy and suggest a minimal resolution. Do not change requirements merely to match accidental behavior.

## 5. Main application flow

```text
app.py / python -m obsidrop
          |
          v
     obsidrop.main
          |
          +--> Build Tkinter main window
          |
          +--> ConfigStore.load() --> AppConfig / validate_config()
          |
          +--> HotkeyManager (when configuration is valid)
          |       |
          |       +--> Dedicated worker thread
          |               +--> RegisterHotKey(Ctrl+Alt+Space)
          |               +--> Windows GetMessage loop
          |               +--> queue.put("capture")
          |
          +--> Tk root.after() polls the event queue
                  |
                  +--> CaptureWindow.show()
                          |
                          +--> User enters text
                          +--> Save callback
                                  |
                                  v
                              write_capture()
                                  +--> Revalidate vault and destination
                                  +--> Create destination folder if needed
                                  +--> Check resolved path remains in vault
                                  +--> Render Markdown
                                  +--> Create unique file using "x" mode
                                  +--> Flush and fsync
```

This is a conceptual map. Inspect current source before relying on any detail or changing behavior.

## 6. Critical invariants — never break these

### 6.1 Vault boundary
- The selected vault root is the storage boundary.
- The destination folder must always be relative to that root.
- Never allow a configured destination to write outside the vault.
- Validate paths when settings are saved and revalidate immediately before writing.
- Resolve paths and check containment after creating the destination directory; a symlink could redirect a path.
- Reject absolute paths, drive-qualified paths, parent traversal (`..`), invalid Windows filename characters, reserved Windows device names, and invalid trailing spaces/periods.
- Do not assume a path is still safe just because it was safe when settings were saved.

### 6.2 Never overwrite an existing note
- Use exclusive file creation (`open(..., "x", ...)`) or an equivalently safe atomic mechanism.
- On collision, generate another filename; do not replace the existing file.
- Preserve existing file content byte-for-byte.
- Do not rely only on a check-then-write sequence; another process could create the file between those operations.

### 6.3 Preserve the user's draft
- If saving fails, do not clear or close the capture window.
- Show a useful error and leave the text available for retry.
- Never silently discard text because of an error.
- Do not automatically delete a partial file after a low-level write failure; report the issue and preserve evidence for recovery.

### 6.4 Local-first privacy
- v0.0.1 makes no network requests and uses no cloud or AI service.
- Never log note bodies.
- Keep settings and logs outside the vault.
- Do not inspect clipboard, foreground-window content, screenshots, or other context.
- Do not add telemetry or analytics.

### 6.5 Unicode and Markdown
- Use UTF-8 for notes and JSON configuration.
- Preserve multiline text and Bangla/Unicode characters.
- Keep output plain Markdown with the existing frontmatter fields unless requirements are intentionally changed.
- Do not add dependencies for ordinary Markdown output.

## 7. Tkinter and threading rules

This is a critical implementation constraint:
- Tkinter is not thread-safe. Create, read, update, and destroy widgets only on the Tkinter main thread.
- `hotkeys.py` owns the worker thread and Windows message pump.
- The worker communicates with the GUI through the thread-safe `queue.Queue[str]` passed to `HotkeyManager`.
- `main.py` polls the queue using `root.after(...)`.
- The worker may enqueue simple event strings such as `"capture"` or `"hotkey_error:..."`; it must never call Tk methods.
- Release the registered shortcut during normal application shutdown.
- If hotkey registration fails, the app must remain usable through **Capture now**.
- Do not block the Tkinter main thread with long-running work or introduce a second GUI event loop.

Why: Windows associates a thread-registered hotkey with that thread's message queue. A dedicated worker processes Windows messages while Tkinter runs normally. The queue is the safe bridge between threads.

## 8. Configuration and file-format details

- `AppConfig` is an immutable dataclass with `vault_path` and `capture_folder`.
- Default destination: `Inbox/Quick Captures`.
- Configuration schema version: currently `1`.
- Windows settings path: `%APPDATA%\Obsidrop\config.json`.
- On non-Windows development hosts, `config.py` uses XDG config or `~/.config/Obsidrop`; this does not make the native hotkey portable.
- Preserve recoverable config writes (temporary file plus replacement).
- Create the capture destination only when a note is saved, not when settings are merely saved.
- Filename format: `YYYY-MM-DD-HHMMSS.md`, with `-01`, `-02`, etc. on collisions.
- Current frontmatter fields: `created` (quoted timezone-aware local ISO timestamp), `type: capture`, and `source: desktop`.
- The body is the user's text followed by a newline.

Do not casually change the configuration schema or frontmatter. Consider backward compatibility and update tests/docs if a change is required.

## 9. UI behavior

Main window:
- Choose vault folder using a folder picker.
- Enter a vault-relative capture folder.
- Save settings.
- Open the configured vault folder.
- Open capture window manually.
- Quit the application.
- Display configuration, hotkey, and capture status.

Capture window:
- Multiline text editor.
- Save and Cancel buttons.
- `Ctrl + Enter` saves; `Esc` cancels.
- If already open, a second shortcut focuses the existing window; it must not destroy the draft or create duplicates.
- On save error, display the error and preserve entered text.

Keep the UI deliberately simple. Do not add panels or settings without a documented need.

## 10. Environment and dependencies

- Target OS: Windows 10/11.
- Python: 3.10+.
- GUI: built-in Tkinter/ttk.
- Native hotkey: `ctypes` calls to Win32 `user32` and `kernel32`.
- Tests: built-in `unittest`.
- Runtime packages: no third-party dependencies.

Before adding a dependency, explain: (1) the concrete requirement it solves, (2) why the standard library is insufficient, (3) maintenance/security/licensing/network implications, and (4) setup and packaging impact. Do not add packages just because a tutorial or coding agent commonly uses them.

## 11. Testing policy

Run from the repository root:

```powershell
python -m unittest discover -v
python -m compileall -q app.py obsidrop tests
```

- Add/update tests whenever behavior changes.
- Test failure cases as well as happy paths.
- Use temporary directories; never write tests into a real personal vault.
- Tests must not depend on the user's real `%APPDATA%`, vault, or notes.
- Symlink and junction tests may need to skip where the host/account cannot create them.
- Linux/macOS test success does not verify Windows APIs or Windows Tk focus behavior.
- CI (`.github/workflows/tests.yml`) runs the suite on Windows and Linux for Python 3.14 and 3.15; 3.10–3.13 remain allowed by `pyproject.toml` but are no longer covered by CI. CI does not replace manual Windows verification.
- Never claim a manual Windows test passed unless it was actually performed on Windows.

Manual Windows checks include first launch, vault selection, config persistence, hotkey from Notepad/browser, saving with Obsidian closed, Bangla/multiline text, save/cancel/error draft retention, collision behavior, hotkey conflict fallback, and shutdown releasing the shortcut. See `docs/TEST_PLAN.md` for the full matrix.

## 12. Required workflow for every task

### Before editing
1. Read this file and relevant specification/architecture/test documents.
2. Inspect current source; do not rely on memory or this summary alone.
3. Restate the requested outcome briefly.
4. Identify files likely to change and why.
5. Identify acceptance criteria and edge cases.
6. Ask one concise question only if an essential requirement is ambiguous; otherwise state a conservative assumption and proceed.

### While editing
1. Make the smallest change that satisfies the request.
2. Preserve module boundaries and all safety invariants.
3. Add/update tests with behavior changes.
4. Avoid unrelated refactors and speculative features.
5. Do not install packages or run destructive commands without permission.
6. Keep documentation aligned with actual code.
7. Do not claim code has been run on Windows if it has not.

### Before reporting completion
1. Run unit tests and compile check.
2. Inspect the diff for accidental changes, secrets, generated files, and unrelated edits.
3. List exact files changed.
4. State exact commands and pass/fail results.
5. State what was not tested, especially Windows-only behavior.
6. Explain important decisions in language suitable for a Python beginner.
7. Give concrete manual test steps where needed.
8. Update `CHANGELOG.md` for release-visible changes.

## 13. Guidance for AI agents

The project owner is learning Python and may use smaller coding models. Therefore:
- Do not assume advanced Python, Win32, threading, or packaging knowledge.
- Explain unfamiliar terms briefly in reports.
- Prefer explicit, maintainable code over clever code.
- Do not infer current requirements from roadmap ideas.
- Do not invent files, tests, commands, dependencies, or completed verification.
- Split oversized tasks into small implementation stages.
- When asked to implement, make the requested changes rather than only giving generic advice.
- When asked to review, separate confirmed defects from possible risks and style preferences.
- Be direct about uncertainty and limitations.

## 14. Definition of done

A task is complete only when the requested behavior exists; safety invariants still hold; relevant tests cover the change; tests and compilation have been run and results reported; Windows-only behavior is tested or explicitly marked unverified; docs/changelog are updated as appropriate; no unrequested dependency or roadmap feature was added; and the final report accurately describes changed files, verification, and remaining limitations.
