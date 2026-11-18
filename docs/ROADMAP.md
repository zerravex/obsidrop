# Roadmap — proposed direction

This roadmap is a planning document, not a promise that every item will ship. Priorities should be adjusted using real usage and bug reports. Keep releases small and preserve the lightweight, local-first character of Obsidrop.

## v0.0.1 — Core capture (current)

- First-run vault configuration.
- Vault-relative capture destination.
- Global `Ctrl + Alt + Space` shortcut on Windows.
- Floating multiline text window.
- Direct UTF-8 Markdown writing.
- Timestamp filenames and collision avoidance.
- Basic validation, error handling, logging, and tests.

## v0.0.2 — Reliability and polish

- Better shortcut-conflict diagnostics.
- More resilient behavior when a vault drive is disconnected or remounted.
- Clearer save status and recovery messages.
- Improved window placement and keyboard focus behavior.
- Additional automated tests for Windows path corner cases.
- Consider single-instance protection only if real use demonstrates duplicate launches are a problem.

## v0.1.0 — Background utility

- System-tray icon and menu.
- Close-to-tray option.
- Start with Windows toggle.
- Configurable global shortcut.
- A settings window separated from the main control/status window.
- Optional launch-at-login shortcut or Windows startup integration.

## v0.2.0 — Explicit context capture

- User-invoked clipboard capture (not silent clipboard monitoring).
- Explicit selected-text capture where supported, using a carefully tested clipboard workflow.
- Optional active application name and window title metadata.
- Multiple capture templates.
- Better capture history and quick-open destination.

## v0.3.0 — Capture organization

- Named capture types such as Thought, Idea, Task, Link, and Quote.
- User-configurable Markdown templates.
- Multiple vault-relative destinations and explicit routing rules.
- Optional append-to-daily-note mode with conflict-aware file handling.
- Filename formatting options.

## v0.4.0 — Visual and file capture

- Screenshot capture initiated by the user.
- Image and file attachments.
- Configurable attachment folder.
- Markdown references to stored assets.
- Clear warnings for large files and unsupported formats.

## v0.5.0 — Browser extension

- Companion extension for Chromium-based browsers, initially Chrome, Edge, and Brave.
- Capture page URL and title.
- Capture selected text and page metadata.
- User-configurable web clipping templates.
- A small local communication protocol between the extension and desktop app, with origin validation and explicit permissions.

## v0.6.0 — Obsidian companion plugin

- Optional plugin for configuring or inspecting Obsidrop from Obsidian.
- Capture history and destination management.
- Optional note linking and Obsidian-specific workflows.
- Core capture must continue to work when Obsidian is closed.

## v0.7.0 — Workflow intelligence

- User-defined event/routing rules.
- Optional AI classification and enrichment.
- User review before consequential automated actions.
- Integrations with a broader Personal Knowledge Operating System.

## v1.0.0 — Stable release

- Stable configuration migration strategy.
- Full Windows compatibility testing.
- Installer and code-signed distribution.
- Upgrade and recovery documentation.
- Security/privacy review of any extension or local API.
- Documented support policy and release process.

## Prioritization principles

1. Fix data-loss and destination bugs before adding features.
2. Prefer frequently used, low-friction improvements.
3. Keep AI optional and out of the critical capture path.
4. Preserve Markdown portability and local-first operation.
5. Add integrations only when they solve a demonstrated workflow problem.
