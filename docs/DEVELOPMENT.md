# Development Guide

## 1. Prerequisites

- Windows 10 or Windows 11 (64-bit) for packaging and full application testing.
- Python 3.14 (64-bit) with Tcl/Tk support.
- Git.
- VS Code or another Python editor.
- Internet access only when installing the pinned PyInstaller build dependency.

The application has no third-party runtime dependencies in v0.0.1. PyInstaller is a build-time dependency only.

## 2. Set up a local development environment

From PowerShell in the repository root:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python --version
python -m tkinter
```

If PowerShell execution policy prevents activation, invoke the environment's interpreter directly:

```powershell
.venv\Scripts\python.exe app.py
```

For packaging, create a separate build environment so PyInstaller is not mixed into the runtime environment:

```powershell
py -3.14 -m venv .venv-build
.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
```

## 3. Run the application

```powershell
python app.py
```

Or:

```powershell
python -m obsidrop
```

## 4. Run automated checks

```powershell
py -3.14 -m unittest discover -v
py -3.14 -m compileall -q app.py obsidrop tests
```

The global hotkey is Windows-specific. Run the manual test matrix in `TEST_PLAN.md` on Windows.

CI (`.github/workflows/tests.yml`) runs the same unit-test and compilation commands on Windows and Linux for Python 3.14 and 3.15 using the GitHub-hosted runners. Linux runners may skip tests that import Tkinter when the Tk runtime is unavailable. CI does not replace the manual Windows hotkey and GUI checks. Python 3.14 is the minimum supported version.

## 5. Suggested AI-assisted workflow

1. Read `AGENTS.md`, `PRODUCT_SPEC.md`, and `ARCHITECTURE.md`.
2. Ask the agent to inspect the repository and describe the smallest change it plans to make.
3. Work on one vertical slice or bug at a time.
4. Ask for tests to be added with each behavior change.
5. Run the automated tests locally.
6. Manually test Windows-specific behavior.
7. Ask for an independent code review of the diff.
8. Commit a working state before beginning the next feature.
9. Update `CHANGELOG.md`, `README.md`, and the specification when user-visible behavior changes.

Useful instruction: do not allow an agent to add dependencies, rewrite unrelated modules, or implement roadmap items without an explicit decision.

## 6. Git workflow

Initialize the repository if needed:

```powershell
git init
git add .
git commit -m "Create Obsidrop v0.0.1 project"
```

After each verified feature:

```powershell
git status
git diff
git add .
git commit -m "Describe the verified change"
```

Do not commit `.venv`, user settings, logs, or test vault contents.

## 7. Build the Windows portable release

Packaging requires Windows x64 and Python 3.14. PyInstaller is pinned in `requirements-build.txt`; do not install it into the application's runtime environment or add it to `dependencies` in `pyproject.toml`.

From the repository root:

```powershell
py -3.14 -m venv .venv-build
.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
.venv-build\Scripts\python.exe scripts\build_release.py
```

The build script is the single entry point used by both local development and `.github/workflows/release.yml`. It:

1. Reads the version from `pyproject.toml` and checks that `obsidrop/__init__.py` agrees.
2. Refuses to run on a non-Windows host, with a Python version other than 3.14, or without PyInstaller.
3. Runs PyInstaller in one-folder, windowed mode:

   ```powershell
   python -m PyInstaller --noconfirm --clean --onedir --windowed --name Obsidrop --distpath dist --workpath build/pyinstaller --specpath build/pyinstaller app.py
   ```

4. Verifies that `Obsidrop.exe` is x64 and uses the Windows GUI subsystem, so Windows does not create a console window.
5. Verifies that the bundled Python runtime, Tkinter extension, and Tcl/Tk runtime libraries and script data are present. Tcl/Tk 9 keeps the script data inside the runtime DLLs; older versions use loose `init.tcl` and `tk.tcl` files.
6. Stages `Obsidrop-0.0.1-Windows-x64`, copies `README-portable.txt` to `README.txt` and `LICENSE` to `LICENSE.txt`, and creates the ZIP from that staging directory.
7. Writes the SHA-256 checksum after the ZIP is finalized and verifies it again.

The generated assets are:

```text
release\Obsidrop-v0.0.1-Windows-x64.zip
release\Obsidrop-v0.0.1-Windows-x64.zip.sha256
```

To validate a release tag locally, pass it to the same script. A mismatch fails before the build:

```powershell
.venv-build\Scripts\python.exe scripts\build_release.py --tag v0.0.1
```

Verify the checksum independently:

```powershell
Get-FileHash -Algorithm SHA256 .\release\Obsidrop-v0.0.1-Windows-x64.zip
Get-Content .\release\Obsidrop-v0.0.1-Windows-x64.zip.sha256
```

The hash and filename must match the checksum file. To inspect the archive structure:

```powershell
Expand-Archive .\release\Obsidrop-v0.0.1-Windows-x64.zip -DestinationPath "$env:TEMP\obsidrop-zip-check" -Force
Get-ChildItem "$env:TEMP\obsidrop-zip-check\Obsidrop-0.0.1-Windows-x64"
```

The folder must contain `Obsidrop.exe`, `_internal\`, `README.txt`, and `LICENSE.txt`. Do not distribute only the executable; the `_internal` runtime files are required.

Do not commit `build/`, `dist/`, or `release/` output. This process produces a portable ZIP, not an installer or a code-signed release. The release workflow publishes assets only for a pushed tag that matches the project version; a manual workflow run produces downloadable artifacts only.

## 8. Definition of done

A task is done only when:

- Its acceptance criteria are met.
- Relevant automated tests pass.
- Windows-only behavior has been manually tested when applicable.
- No unrelated regressions are known.
- Documentation and changelog are updated as needed.
- The agent reports what was tested and what remains unverified.
