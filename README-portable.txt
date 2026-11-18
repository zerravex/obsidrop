Obsidrop 0.0.1 - Windows Portable
=================================

Obsidrop is a small, local-first desktop utility for capturing a thought from
anywhere on Windows and saving it as a Markdown file inside a folder you choose,
usually an Obsidian vault.

Obsidian does not need to be installed or running. Obsidrop writes a normal .md
file directly into the selected folder. It makes no network requests and has no
telemetry.


Before you start
----------------

- Target platforms: Windows 10 and Windows 11 (64-bit).
- The v0.0.1 portable build was smoke-tested on Windows 10 x64. Windows 11 has
  not been separately verified for this build.
- Python does not need to be installed.
- Keep Obsidrop.exe and the _internal folder together. Do not move or delete
  _internal.
- Extract the whole ZIP to a normal folder before running the application.
- This build is not digitally signed. Windows SmartScreen may show a warning
  for an unsigned application.


Run Obsidrop
------------

1. Extract Obsidrop-v0.0.1-Windows-x64.zip.
2. Open the extracted Obsidrop-0.0.1-Windows-x64 folder.
3. Double-click Obsidrop.exe.
4. On first launch, choose your Obsidian vault folder.
5. Keep the default capture folder, Inbox/Quick Captures, or enter another
   folder relative to the vault.
6. Click Save settings.
7. Press Ctrl + Alt + Space from any application, or click Capture now.
8. Type or paste your text, then press Ctrl + Enter or click Save capture.
9. Press Esc or click Cancel to discard the current draft.
10. Quit with the Quit button or by closing the main Obsidrop window.

If the global shortcut is unavailable, another application may already be using
Ctrl + Alt + Space. Use Capture now instead. After closing the conflicting
application, save your settings again to retry registration.


Settings and logs
-----------------

Obsidrop stores configuration and logs outside the vault, in your Windows user
profile:

  %APPDATA%\Obsidrop\config.json
  %APPDATA%\Obsidrop\logs\obsidrop.log

The extracted application folder is not used for settings or logs. Logs may
contain local file paths and Windows error details; review them before sharing.
Captured note bodies are not written to the log.


License
-------

Obsidrop is released under the MIT License. The full license text is included
in LICENSE.txt in this folder.


Notes about this release
------------------------

This is an early v0.0.1 release. Test it with a disposable vault before relying
on it for important information, and keep normal backups of your notes.
