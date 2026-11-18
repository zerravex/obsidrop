# Changelog

All notable project changes are recorded here. This project is currently an early release.

## [0.0.1] — First official release

The first official release includes the initial application, reliability and
security hardening, and a Windows x64 portable build with release automation.

### Added

- Standalone Python/Tkinter desktop application.
- First-run vault and capture-folder configuration.
- Global `Ctrl + Alt + Space` hotkey implementation for Windows.
- Manual **Capture now** fallback.
- Floating multiline capture window with `Ctrl + Enter` save and `Esc` cancel.
- Direct UTF-8 Markdown file creation.
- Timezone-aware creation metadata and collision-safe filenames.
- Vault-relative path validation and symlink containment checks.
- JSON configuration outside the vault.
- Rotating application log.
- Standard MIT license.
- Automated tests for configuration, path validation, Markdown rendering, and file creation.
- Agent instructions, product specification, architecture, development, privacy, test plan, and roadmap documentation.
- Regression tests for Markdown trailing-newline preservation, schema-version types, reserved Windows names, path containment, symlinks/junctions, write failures, hotkey retry and worker failures, and logging recovery.
- Shared filesystem test helpers for symlink or Windows junction tests.
- Minimal GitHub Actions workflow (`.github/workflows/tests.yml`) running tests on Windows and Linux with Python 3.14 and 3.15.
- Scripted Windows x64 portable build using PyInstaller 6.22.3 in one-folder, windowed mode with Python 3.14.
- `scripts/build_release.py`, which validates project and package versions, optionally validates a Git tag, builds the application, verifies the x64 GUI subsystem and bundled Python/Tcl/Tk runtimes, stages the portable distribution, creates the release ZIP, and writes and verifies its SHA-256 checksum.
- `README-portable.txt` as the source for the packaged `README.txt`.
- The portable ZIP includes the MIT license as `LICENSE.txt`.
- `.github/workflows/release.yml` for manual test builds and tag-triggered release publication, with separate read-only build and write-enabled publish permissions.
- `requirements-build.txt`, which pins PyInstaller as a build-only dependency.

### Fixed

- Intentional trailing blank lines in captured Markdown are no longer removed; line endings are normalized to LF and one final newline is ensured.
- Configuration schema versions must be the exact integer `1`; booleans, floats, strings, and missing/unsupported versions are rejected.
- Windows reserved-name validation now covers superscript `COM¹`/`LPT¹` variants, `CONIN$`/`CONOUT$`, mixed capitalization, and reserved names followed by an extension.
- Destination folders ending in whitespace are rejected instead of being silently trimmed.
- A failed global-shortcut registration can be retried after the user resolves the conflict and saves settings again, without restarting the application.
- Runtime hotkey worker failures and unexpected listener exits are reported to the GUI through the existing event queue.
- Logging initialization can recover after the log directory becomes available, is retried when settings are saved, and no longer leaves a permanent fallback handler.

### Changed

- Minimum supported Python is now 3.14. CI covers Python 3.14 and 3.15.
- Automated tests now resolve temporary vault paths on Windows, fixing failures caused by 8.3 short-path comparison.
- Updated development, test, and agent documentation for the portable release process.

### Not included

- No runtime dependencies, network access, database, tray behavior, startup registration, or new capture features were added.
- No installer, code signing, automatic updates, or automatic tag creation is included.
- Clipboard capture, browser extension, Obsidian plugin, and AI features remain out of scope.
