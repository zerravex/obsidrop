# Obsidrop

**Version:** `0.0.1`  
**Status:** Early prototype / first development release  
**Primary platform:** Windows 10 and Windows 11  
**Minimum Python:** 3.10  
**Runtime dependencies:** Python standard library only  
**License:** Not yet selected

Obsidrop is a lightweight, local-first desktop utility for capturing thoughts from anywhere on your Windows desktop and saving them as Markdown files inside a folder you choose—usually an [Obsidian](https://obsidian.md/) vault.

The goal is simple: reduce the distance between *having a thought* and *saving it somewhere useful*.

**Obsidian does not need to be open—or even running—when Obsidrop saves a capture.** An Obsidian vault is a normal folder containing Markdown files and optional Obsidian metadata. Obsidrop writes a regular `.md` file directly into that folder.

---

## 1. The basic workflow

1. Start Obsidrop.
2. Select the root folder of your Obsidian vault.
3. Choose a destination folder inside the vault. The default is `Inbox/Quick Captures`.
4. Press `Ctrl + Alt + Space` anywhere in Windows, or click **Capture now**.
5. Type or paste your thought into the floating window.
6. Press `Ctrl + Enter` or click **Save capture**.
7. Obsidrop creates a new Markdown file in the configured destination.

### Example output

A capture made at 12:15:30 local time on 17 November 2026 could create:

```text
Your Obsidian Vault/
└── Inbox/
    └── Quick Captures/
        └── 2026-11-17-121530.md
```

The resulting file looks like:

```markdown
---
created: "2026-11-17T12:15:30+06:00"
type: capture
source: desktop
---

The note content goes here.
```

The timestamp is illustrative; the actual timestamp and UTC offset come from the computer's local clock. If the filename already exists, Obsidrop tries `-01`, `-02`, and so on. It uses exclusive file creation, so it does not intentionally overwrite an existing note.

## 2. What v0.0.1 includes

- Standalone Python desktop application.
- Global Windows shortcut: `Ctrl + Alt + Space`.
- Floating multiline capture window.
- `Ctrl + Enter` to save and `Esc` to cancel.
- First-run selection of an existing vault folder.
- Configurable destination folder relative to the vault; default `Inbox/Quick Captures`.
- Direct Markdown creation; no Obsidian CLI, URI, plugin, or running Obsidian process is required.
- Timestamped filenames with collision-safe numeric suffixes.
- UTF-8 output, including Bangla and other Unicode text.
- Configuration and logs stored outside the vault.
- Basic path validation and checks against destination symlinks escaping the vault.
- Automated tests using Python's built-in `unittest`.

## 3. What v0.0.1 deliberately does not do

These are intentionally excluded from the first release:

- Clipboard monitoring or automatic clipboard capture.
- Reading selected text from other applications.
- Inspecting foreground-window titles or contents.
- Screenshots or attachments.
- System tray or run-at-login behavior.
- Configurable global shortcut.
- Appending to daily notes or editing existing notes.
- Browser extension or Obsidian companion plugin.
- AI categorization, AI API calls, or cloud service.
- Accounts, telemetry, analytics, or network requests.
- Database, background service, installer, or packaged `.exe`.

Potential later features are documented in [`docs/ROADMAP.md`](docs/ROADMAP.md). A roadmap item is not part of the current release.

## 4. Requirements

- Windows 10 or Windows 11 for the intended full experience.
- Python 3.10 or newer. Python 3.12+ is a sensible choice for a new installation.
- Tkinter support. It is normally included with the standard Windows Python installer; ensure Tcl/Tk support is selected.
- A folder in which to store Markdown notes. An existing Obsidian vault is recommended but not technically required.

No third-party Python packages are required by v0.0.1. There is no `pip install` step.

## 5. Install and run from source

### Option A — Windows launcher

1. Install Python for Windows from [python.org](https://www.python.org/downloads/windows/).
2. During installation, enable the Python launcher and Tcl/Tk support.
3. Download and extract the Obsidrop project ZIP.
4. Open the extracted `Obsidrop` folder.
5. Double-click `run_obsidrop.bat`.

The launcher creates a local `.venv` virtual environment if one does not exist, then starts Obsidrop. It does not install third-party packages.

### Option B — PowerShell

Open PowerShell in the extracted project folder and run:

```powershell
# Create an isolated Python environment (first run only)
py -3 -m venv .venv

# Start the application
.venv\Scripts\python.exe app.py
```

You can activate the environment first if preferred:

```powershell
.venv\Scripts\Activate.ps1
python app.py
```

If PowerShell blocks script activation, use the direct `.venv\Scripts\python.exe app.py` command. Activation is optional.

You can also run the package entry point:

```powershell
python -m obsidrop
```

## 6. First launch and setup

1. Start Obsidrop.
2. Under **Obsidian vault folder**, click **Browse…**.
3. Select the root folder of your vault. For a normal Obsidian vault, this is the folder containing the hidden `.obsidian` folder.
4. Set **Capture folder (relative to the vault)**. Keep the default `Inbox/Quick Captures` or enter another relative folder.
5. Click **Save settings**.
6. Check the status area. Obsidrop attempts to register `Ctrl + Alt + Space`.
7. Click **Capture now** to test the capture window immediately.

The destination folder is created when the first note is saved. Saving settings alone does not create it.

### Destination examples

| Destination | Result |
|---|---|
| `Inbox/Quick Captures` | Valid nested folder |
| `Inbox/Ideas` | Valid nested folder |
| `Clippings` | Valid folder inside the vault |
| `Research/Reading Notes` | Valid nested folder |
| `C:/Notes` | Invalid: absolute / drive-qualified path |
| `../OutsideVault` | Invalid: parent traversal |
| `/Notes` | Invalid: absolute path |

Use a relative folder path only. Forward slashes are recommended; backslashes are also normalized.

## 7. Everyday use

### Open the capture window
- Press `Ctrl + Alt + Space` from another application.
- Or click **Capture now** in the main Obsidrop window.

### Save a capture
- Type or paste text into the multiline field.
- Press `Ctrl + Enter`, or click **Save capture**.
- A successful save closes the capture window and displays the saved path in the main window.

### Cancel a capture
- Press `Esc`, or click **Cancel**.
- Cancelling explicitly discards the current draft.

### If the global shortcut is unavailable
Another program may already have registered `Ctrl + Alt + Space`. Obsidrop reports the problem, but **Capture now** remains available. Some games or exclusive-fullscreen applications may also intercept global shortcuts.

## 8. How the project works

```text
app.py / python -m obsidrop
          |
          v
     obsidrop.main
          |
          +--> Main Tkinter window and application lifecycle
          +--> config.py: validate vault, load/save JSON settings
          +--> hotkeys.py: Windows shortcut on a worker thread
          |       +--> queue event sent to Tkinter main thread
          +--> capture_window.py: floating multiline editor
          +--> markdown_writer.py: render and safely write Markdown
```

### Why write Markdown directly?
An Obsidian vault is a folder of files. A normal Markdown file placed in the vault can be opened and indexed by Obsidian. Direct filesystem writing means Obsidian does not have to be running, Obsidrop does not depend on Obsidian's CLI or URI handling, and the note remains readable in any Markdown editor. Obsidrop is a companion utility, not an Obsidian plugin.

### Why is the hotkey on a separate thread?
The Windows hotkey API uses a Windows message queue associated with the thread that registers the shortcut. Obsidrop keeps that message loop on a dedicated worker thread. The worker sends a small event through a thread-safe queue; the Tkinter main thread receives it and opens the capture window. Tkinter widgets are only manipulated on the main thread.

## 9. Project structure

```text
Obsidrop/
├── app.py                       # Main source launcher
├── run_obsidrop.bat            # Windows quick launcher
├── requirements.txt             # No third-party runtime packages required
├── pyproject.toml               # Project metadata and Python version
├── .gitignore                   # Excludes local/generated files
├── AGENTS.md                    # Persistent context and instructions for AI agents
├── README.md                    # This user-facing guide
├── CHANGELOG.md                 # Version history
│
├── obsidrop/                   # Application source package
│   ├── __init__.py              # Package version
│   ├── __main__.py              # Enables `python -m obsidrop`
│   ├── main.py                  # Main window and application coordination
│   ├── config.py                # Settings, JSON persistence, path validation
│   ├── hotkeys.py               # Windows global shortcut handling
│   ├── capture_window.py        # Floating capture interface
│   ├── markdown_writer.py       # Markdown generation and safe file writing
│   └── logging_setup.py         # Application logging
│
├── tests/                       # Automated tests
│   ├── __init__.py
│   ├── test_config.py           # Config and path validation tests
│   └── test_markdown_writer.py  # Markdown and file-writing tests
│
└── docs/                        # Detailed project documentation
    ├── PRODUCT_SPEC.md          # Product behavior and acceptance criteria
    ├── ARCHITECTURE.md          # Technical design and module boundaries
    ├── DEVELOPMENT.md           # Setup and contributor workflow
    ├── TEST_PLAN.md             # Automated and manual test cases
    ├── PRIVACY_AND_DATA.md      # Data handling and privacy
    └── ROADMAP.md               # Potential future releases
```

### Important source files

| File | Responsibility |
|---|---|
| `obsidrop/main.py` | Coordinates app, settings window, capture window, hotkey events, and shutdown |
| `obsidrop/config.py` | Validates vault/destination and stores/loads settings |
| `obsidrop/hotkeys.py` | Registers and releases the Windows global shortcut |
| `obsidrop/capture_window.py` | Implements the floating text-entry window |
| `obsidrop/markdown_writer.py` | Builds Markdown and safely creates the note file |
| `obsidrop/logging_setup.py` | Configures the rotating log file |

## 10. Markdown format and filename behavior

Each successful capture creates one new Markdown file. Current frontmatter:

```yaml
---
created: "2026-11-17T12:15:30+06:00"
type: capture
source: desktop
---
```

`created` is a timezone-aware local timestamp. The body follows the blank line after the frontmatter.

Filename format: `YYYY-MM-DD-HHMMSS.md`. If already taken, Obsidrop tries a numeric suffix (`-01`, `-02`, etc.). Exclusive creation (`x` mode) fails rather than replacing an existing file. The destination is revalidated before writing and checked to remain inside the selected vault.

## 11. Configuration, logs, and stored data

On Windows, Obsidrop stores application settings and logs outside the vault:

```text
%APPDATA%\Obsidrop\
├── config.json
└── logs\
    └── obsidrop.log
```

The configuration contains the selected vault path and relative capture folder. Logs record application events and errors, not the body of captured notes. The vault receives only Markdown files the user explicitly saves.

## 12. Privacy and data handling

In v0.0.1:
- No account is required.
- No network requests are made.
- No cloud service or AI API is used.
- The clipboard is not monitored.
- The active application's text or window title is not read.
- No screenshots are taken.
- Note content is written locally only after the user saves.
- Settings and logs are stored outside the vault.
- Administrator privileges are not required.

Vault-boundary checks are protective application logic, not a security sandbox against another malicious process running as the same Windows user. Keep normal backups of important notes. See [`docs/PRIVACY_AND_DATA.md`](docs/PRIVACY_AND_DATA.md).

## 13. Troubleshooting

### The shortcut does not work
1. Confirm Obsidrop is still running.
2. Check the status text in the main window.
3. Another application may own `Ctrl + Alt + Space`; use **Capture now** as a fallback.
4. Some games and exclusive-fullscreen applications may intercept global shortcuts. Try borderless-windowed mode.
5. Restart Obsidrop after closing a conflicting application.

### The app says the vault cannot be accessed
- Confirm that the selected folder still exists.
- Confirm that the current Windows account can write to it.
- Reconnect a removable drive if the vault is stored there.
- Select the correct folder again and save settings.

### A capture folder is rejected
The destination must be relative to the vault. Do not use a drive letter, leading slash, `..`, Windows-reserved device names, or invalid Windows filename characters.

### Tkinter cannot start
Run:

```powershell
python -m tkinter
```

If no test window appears, rerun the Python installer and enable Tcl/Tk support.

### Where are the logs?
Open `%APPDATA%\Obsidrop\logs\obsidrop.log`. Logs may contain local file paths and operating-system error details. Review and sanitize them before sharing.

### A note was not saved
- Check the error shown in the capture window.
- Confirm the destination drive is connected and writable.
- Check whether security software or another process is locking the destination.
- On save failure, the capture window should remain open with the draft so you can retry.
- Do not assume a note was saved unless Obsidrop reports success and the file exists.

## 14. Development and testing

Prerequisites: Python 3.10+ with Tkinter. Git and VS Code are recommended but optional.

Create an environment and run the app:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe app.py
```

Run automated tests:

```powershell
python -m unittest discover -v
```

Run a syntax/bytecode compilation check:

```powershell
python -m compileall -q app.py obsidrop tests
```

The automated suite tests configuration, path validation, Markdown generation, and filesystem behavior. The Windows global hotkey and actual Tk window focus behavior must be manually tested on Windows. Passing tests on Linux does not prove that the Windows API works.

### Recommended reading order for contributors and AI agents
1. [`AGENTS.md`](AGENTS.md) — project context, rules, invariants, and coding workflow.
2. [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — exact v0.0.1 requirements.
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — technical design.
4. [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) — expected verification.
5. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — development workflow.
6. [`docs/PRIVACY_AND_DATA.md`](docs/PRIVACY_AND_DATA.md) — data-handling rules.
7. [`docs/ROADMAP.md`](docs/ROADMAP.md) — future ideas, not current scope.

Before changing behavior, an agent should inspect the source, identify the smallest required change, add tests, run checks, and report what was not tested. Do not let an agent add dependencies or implement roadmap features without an explicit decision.

## 15. Current limitations and release status

- The global shortcut is fixed to `Ctrl + Alt + Space`.
- There is no system tray or run-at-login option.
- Captures are separate files; appending to daily notes is unsupported.
- Browser metadata, selected text, screenshots, and attachments are not captured.
- There is no automatic sync or backup system. Use your normal vault backup/sync process.
- If a low-level disk write fails after a file is created, an incomplete file may remain. Obsidrop reports the error and does not silently delete the file.
- The project is source-first; it is not a signed Windows installer or packaged executable.
- The Windows GUI and hotkey still need real-machine verification.

This is an early v0.0.1 prototype. Test it with a disposable vault before relying on it for important information.

## 16. Project documents

- [`AGENTS.md`](AGENTS.md) — persistent instructions for AI coding agents.
- [`CHANGELOG.md`](CHANGELOG.md) — release history.
- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — requirements and acceptance criteria.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture and module responsibilities.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — local development and workflow.
- [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) — automated and manual tests.
- [`docs/PRIVACY_AND_DATA.md`](docs/PRIVACY_AND_DATA.md) — privacy and data handling.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — potential future releases.
