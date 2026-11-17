# Test Plan — Obsidrop v0.0.1

## 1. Test goals

Verify that Obsidrop saves text reliably to the selected vault, never intentionally overwrites an existing note, rejects unsafe paths, preserves Unicode content, and handles common failures without losing the user's current draft.

## 2. Automated tests

The repository uses Python's standard-library `unittest` framework. Run from the repository root:

```powershell
python -m unittest discover -v
```

### Configuration and path validation

- Missing configuration returns `None`.
- Valid configuration saves and loads correctly.
- Malformed JSON produces a recoverable configuration error.
- Missing vault paths are rejected.
- Valid nested relative folders are accepted.
- Backslashes normalize to forward slashes.
- Empty paths, absolute paths, drive-qualified paths, parent traversal, reserved names, and invalid Windows characters are rejected.
- Where supported, a symlink pointing outside the vault is rejected.

### Markdown generation and file creation

- Frontmatter contains a quoted timezone-aware timestamp.
- Frontmatter includes `type: capture` and `source: desktop`.
- Content is saved as UTF-8.
- Bangla and other Unicode characters remain intact.
- Multiline content remains multiline.
- Empty or whitespace-only content is rejected.
- The destination folder is created on demand.
- Repeated captures with the same timestamp create unique filenames.
- Original file content remains unchanged after a collision.
- A symlinked destination outside the vault is rejected where symlink testing is supported.

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
