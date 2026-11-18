# Changelog

All notable project changes are recorded here. This project is currently an early prototype.

## [Unreleased] — Reliability and security hardening

### Fixed

- Intentional trailing blank lines in captured Markdown are no longer removed; line endings are normalized to LF and one final newline is ensured.
- Configuration schema versions must be the exact integer `1`; booleans, floats, strings, and missing/unsupported versions are rejected.
- Windows reserved-name validation now covers superscript `COM¹`/`LPT¹` variants, `CONIN$`/`CONOUT$`, mixed capitalization, and reserved names followed by an extension.
- Destination folders ending in whitespace are rejected instead of being silently trimmed.
- A failed global-shortcut registration can be retried after the user resolves the conflict and saves settings again, without restarting the application.
- Runtime hotkey worker failures and unexpected listener exits are reported to the GUI through the existing event queue.
- Logging initialization can recover after the log directory becomes available, is retried when settings are saved, and no longer leaves a permanent fallback handler.

### Added

- Regression tests for Markdown trailing-newline preservation, schema-version types, reserved Windows names, path containment, symlinks/junctions, write failures, hotkey retry and worker failures, and logging recovery.
- Minimal GitHub Actions workflow (`.github/workflows/tests.yml`) running tests on Windows and Linux with Python 3.10 and 3.14.
- Shared filesystem test helpers for symlink or Windows junction tests.

### Changed

- Automated tests now resolve temporary vault paths on Windows, fixing failures caused by 8.3 short-path comparison.

### Not included

- No runtime dependencies, network access, database, tray behavior, startup registration, or new capture features were added.

## [0.0.1] — Initial project build

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

### Not included

- System tray, start-at-login, clipboard capture, browser extension, Obsidian plugin, AI, and packaged installer.
