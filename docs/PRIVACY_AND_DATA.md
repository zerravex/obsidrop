# Privacy and Data Handling

## v0.0.1 behavior

Obsidrop is designed as a local desktop utility.

- It does not require an account.
- It does not make network requests.
- It does not send note content to an AI provider or other service.
- It does not monitor the clipboard.
- It does not inspect the active application's text or window title.
- It does not take screenshots.
- It writes Markdown only after the user explicitly saves a capture.

## Files created

### In the selected vault

A successful capture creates one `.md` file in the configured vault-relative destination folder.

### Outside the vault

On Windows, settings and logs live under:

```text
%APPDATA%\Obsidrop\
```

The settings file contains the vault path and configured capture folder. The rotating log records application events and errors. It is designed not to record note bodies.

The Windows portable build uses the same `%APPDATA%\Obsidrop` locations. It does not write settings or logs into the extracted application folder or PyInstaller's temporary resource directory.

## User responsibilities

- Choose a vault folder you control.
- Keep normal backups or versioned sync for important notes.
- Review and sanitize logs before sharing them, because paths and operating-system error details may be present.
- Treat the configured vault as the storage boundary. v0.0.1 performs path and symlink checks, but it is not a security sandbox against another malicious process running under the same Windows user account.

## Future integrations

A future browser extension, local API, or AI feature would introduce additional permissions and data flows. Those features must have separate documentation, explicit user controls, and a review of what content is transmitted or stored before they are released.
