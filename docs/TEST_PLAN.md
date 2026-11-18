# Test Plan — Obsidrop v0.0.1

## 1. Test goals

Verify that Obsidrop saves text reliably to the selected vault, never intentionally overwrites an existing note, rejects unsafe paths, preserves Unicode content, and handles common failures without losing the user's current draft.

## 2. Automated tests

The repository uses Python's standard-library `unittest` framework. Run from the repository root:

```powershell
python -m unittest discover -v
```

CI (`.github/workflows/tests.yml`) runs the same suite on GitHub-hosted Windows and Linux runners with Python 3.10 and 3.14, followed by the compilation check. Linux runs may skip tests that import Tkinter when the Tk runtime is unavailable; native Windows hotkey and GUI behavior still requires the manual matrix below.

### Configuration and path validation

- Missing configuration returns `None`.
- Valid configuration saves and loads correctly.
- Malformed JSON produces a recoverable configuration error.
- The schema version must be the exact integer `1`; booleans, floats, strings, a missing version, and older or newer versions are rejected.
- Missing vault paths are rejected.
- Valid nested relative folders are accepted.
- Backslashes normalize to forward slashes.
- Empty paths, absolute paths, drive-qualified paths, parent traversal, reserved names, and invalid Windows characters are rejected.
- Common reserved device names, superscript-digit variants, mixed capitalization, and reserved names with extensions are rejected.
- Invalid trailing whitespace and trailing periods are rejected.
- Valid folder names that merely resemble reserved names are accepted.
- Where supported, a symlink or junction destination outside the vault is rejected, while one that resolves inside the vault is accepted.

### Markdown generation and file creation

- Frontmatter contains a quoted timezone-aware timestamp.
- Frontmatter includes `type: capture` and `source: desktop`.
- Content is saved as UTF-8.
- Bangla and other Unicode characters remain intact.
- Multiline content remains multiline.
- Content with no final newline receives exactly one final newline.
- Intentional trailing blank lines are preserved.
- LF, CRLF, and lone carriage-return inputs are normalized to LF.
- Trailing spaces within content lines are preserved.
- Empty or whitespace-only content is rejected.
- The destination folder is created on demand.
- Nested destination folders are created correctly.
- Repeated captures with the same timestamp create unique filenames.
- Original file content remains unchanged after a collision and after a failed write.
- Invalid destinations, directory-creation failures, and file-write failures produce a `CaptureError` without silently overwriting an existing note.
- A destination symlink or junction outside the vault is rejected where link testing is supported.

### Hotkey coordination

- A failed startup registration can be retried.
- Repeated `start()` calls while the listener is running do not register a second listener.
- A runtime message-loop error or unexpected worker exit places one `hotkey_error:` token in the event queue.
- A startup registration failure is not also reported as a runtime error.
- Non-Windows platforms raise a specific unsupported-platform error.
- These tests use a mocked Win32 boundary. They do not verify native Windows registration or focus behavior.

### Logging

- Logging initialization creates one rotating file handler.
- Repeated initialization does not duplicate handlers or output.
- A failed initialization recovers when the log directory becomes available.
- Failed initialization adds only one fallback `NullHandler`.
- Saving settings retries logging initialization after a startup failure.

### Compilation check

```powershell
python -m compileall -q app.py obsidrop tests
```

## 3. Manual Windows test matrix

These checks must be run on a real Windows 10 or Windows 11 desktop. Linux tests cannot validate native hotkey registration or Tk window focus behavior on Windows.

| ID | Scenario | Expected result |
|---|---|---|
| M-01 | First launch without config | Main window prompts for vault selection. |
| M-02 | Choose an existing vault | Vault path appears in the settings field. |
| M-03 | Save default destination | Settings are saved; no folder is created until capture. |
| M-04 | Restart application | Saved settings are restored. |
| M-05 | Press `Ctrl + Alt + Space` in Notepad | Floating capture window opens. |
| M-06 | Press shortcut while Brave is foreground | Capture window opens above the active desktop app. |
| M-07 | Save a simple thought | One Markdown file appears in the configured folder. |
| M-08 | Save Bangla and multiline text | Content is preserved in UTF-8. |
| M-09 | Press `Esc` | Window closes and no note is created. |
| M-10 | Press `Ctrl + Enter` | Note saves and window closes. |
| M-11 | Save two captures within the same second | Both files exist with different filenames. |
| M-12 | Keep Obsidian fully closed | Capture still saves correctly. |
| M-13 | Register shortcut while another app owns it | Clear warning appears; manual capture remains available. |
| M-14 | Use an invalid/unavailable destination | Error is visible and capture text remains in the window. |
| M-15 | Quit application | Hotkey is released and can be registered again after restart. |
| M-16 | Run while a game is foreground | Shortcut behavior is observed; document any game-specific interception. |
| M-17 | Close the app that owns the shortcut, then click **Save settings** again | Registration is retried without restarting Obsidrop and succeeds. |
| M-18 | Save text with intentional trailing blank lines | The saved Markdown body retains the blank lines and ends with the expected newline. |
| M-19 | Click **Save settings** repeatedly while the shortcut is active | No duplicate registration or duplicate hotkey events occur. |

## 4. Data-safety checks

- Make a test vault containing an existing note with the same timestamp-derived name and verify it is untouched.
- Test a destination folder with an outside-pointing directory symlink where Windows permissions allow creating one.
- Test a disconnected/removable vault drive and confirm the app reports a failure rather than silently changing destinations.
- Inspect the log and verify captured note bodies are not logged.

## 5. Test evidence

For each manual release test, record:

- Windows version and Python version.
- Test ID.
- Pass/fail.
- Steps and observed behavior.
- Error message or sanitized log excerpt if failed.

Do not mark a Windows-specific manual test as passed solely because static code inspection or Linux unit tests succeeded.
