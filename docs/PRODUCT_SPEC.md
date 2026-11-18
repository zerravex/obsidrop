# Product Requirements — Obsidrop v0.0.1

## 1. Product summary

Obsidrop is a lightweight Windows desktop utility that lets a user capture a short thought while working in another application and save it directly as a Markdown file inside a chosen Obsidian vault. The core capture path must work while Obsidian is closed.

## 2. Problem

Capturing an idea currently requires the user to stop their current activity, switch to a note-taking application, navigate to a destination, and create a note. This friction can cause ideas to be forgotten. Obsidrop reduces the interaction to a global shortcut, text entry, and save.

## 3. Target user and environment

- Primary user: an individual Windows user who maintains an Obsidian vault.
- Supported OS: Windows 10 and Windows 11.
- Python: 3.14 or newer for source use; the portable build includes Python.
- Hardware: low- and mid-range Windows computers; avoid unnecessary background CPU and memory use.
- Connectivity: no internet connection required.

## 4. Product principles

- Capture should be fast and predictable.
- Obsidian is a destination, not a runtime dependency.
- Data stays local.
- Markdown files remain human-readable and portable.
- User-selected destinations must be respected.
- Existing notes must never be overwritten.
- The first release should avoid speculative features.

## 5. v0.0.1 functional requirements

### FR-01: First-run configuration

When no valid configuration exists, the application must allow the user to select an existing vault folder and set a vault-relative capture folder. The default destination is `Inbox/Quick Captures`.

### FR-02: Configuration persistence

The selected vault path and capture folder must persist between launches in a JSON file outside the vault. Configuration must include a schema version and be saved safely.

### FR-03: Global shortcut

On Windows, Obsidrop must attempt to register `Ctrl + Alt + Space` globally. Registration failure must be reported. The application must not require administrator privileges.

### FR-04: Manual fallback

The main window must expose a **Capture now** button so that a user can capture even when the global shortcut cannot be registered.

### FR-05: Floating capture window

The capture window must provide a multiline text editor, a save action, a cancel action, and keyboard shortcuts. `Ctrl + Enter` saves; `Escape` cancels.

### FR-06: Markdown output

A successful capture must create one UTF-8 Markdown file with YAML frontmatter containing a local timezone-aware creation timestamp, `type: capture`, and `source: desktop`.

### FR-07: Filename uniqueness

Filenames must be timestamp-based. If a filename already exists, a numeric suffix must be added. Existing files must never be replaced.

### FR-08: Destination safety

The destination must be a relative path under the selected vault. Absolute paths, parent traversal, invalid Windows folder names, and symlink escapes must be rejected.

### FR-09: Unicode support

Bangla and other Unicode content must round-trip through the saved UTF-8 Markdown file.

### FR-10: Error handling

Empty captures must not create files. Configuration, path, and write errors must be communicated without silently discarding the current capture text.

### FR-11: Shutdown

The application must release its registered global shortcut when it exits normally.

### FR-12: Control window

The main window must show the selected vault, destination folder, shortcut state, and basic actions to save settings, capture, open the vault folder, and quit.

## 6. Out of scope for v0.0.1

- System tray and close-to-tray behavior.
- Start with Windows.
- User-configurable hotkeys.
- Clipboard monitoring or explicit clipboard capture.
- Arbitrary application selection capture.
- Active-window title or process capture.
- Browser extension or web clipping.
- Screenshot and file attachment capture.
- AI classification, summarization, or routing.
- Obsidian plugin, CLI, URI, or Local REST API integration.
- Daily-note append mode or multi-destination routing.
- Cloud sync, account system, telemetry, or network access.
- Database storage.
- Installer, code signing, and automatic updates.

## 7. User stories

1. As a user, I can choose my vault and capture folder so new notes go where I expect.
2. As a user, I can press the global shortcut while using another application to open the capture window.
3. As a user, I can use the main-window capture button when the shortcut is unavailable.
4. As a user, I can save multiple captures without filename collisions or overwriting earlier notes.
5. As a user, I can save Bangla, Unicode, and multiline text without corruption.
6. As a user, I can keep Obsidian closed and still capture notes.
7. As a user, I receive a clear error and retain my entered text when a save fails.

## 8. Acceptance criteria

- [ ] A first-run user can select a valid vault and relative folder.
- [ ] Settings persist after restarting the app.
- [ ] On Windows, `Ctrl + Alt + Space` opens the capture window when registered.
- [ ] The manual capture button works independently of hotkey registration.
- [ ] Obsidian can be fully closed while a capture is saved.
- [ ] A saved note appears in the configured directory.
- [ ] Output contains the expected frontmatter and content.
- [ ] Bangla and multiline text remain intact.
- [ ] Repeated captures in the same second create distinct files.
- [ ] An outside-vault or traversal destination is rejected.
- [ ] Blank content is rejected.
- [ ] A save error does not close the capture window or clear its text.
- [ ] Normal application shutdown unregisters the hotkey.

## 9. Success measure

The first release is successful when a Windows user can repeatedly save text into the configured vault from another desktop application, without opening Obsidian, and without data loss or accidental overwrites.
