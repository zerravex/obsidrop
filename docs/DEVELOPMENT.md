# Development Guide

## 1. Prerequisites

- Windows 10 or Windows 11 for full application testing.
- Python 3.10 or newer with Tcl/Tk support.
- Git.
- VS Code or another Python editor.

The application has no third-party runtime dependencies in v0.0.1.

## 2. Set up a local development environment

From PowerShell in the repository root:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python --version
python -m tkinter
```

If PowerShell execution policy prevents activation, invoke the environment's interpreter directly:

```powershell
.venv\Scripts\python.exe app.py
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
python -m unittest discover -v
python -m compileall -q app.py obsidrop tests
```

GitHub Actions runs both checks on Windows and Ubuntu with Python 3.14 and 3.15 (`.github/workflows/tests.yml`). The application still declares Python 3.10+ support in `pyproject.toml`.

The global hotkey is Windows-specific. Run the manual test matrix in `TEST_PLAN.md` on Windows.

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

## 7. Packaging (later)

Packaging is not part of v0.0.1. When the application is stable, evaluate PyInstaller. Start with a one-folder build because it is easier to inspect and troubleshoot. Test the packaged app on a clean Windows account or virtual machine before distributing it. Do not claim that packaging is an installer or code-signed release unless those steps are actually implemented.

## 8. Definition of done

A task is done only when:

- Its acceptance criteria are met.
- Relevant automated tests pass.
- Windows-only behavior has been manually tested when applicable.
- No unrelated regressions are known.
- Documentation and changelog are updated as needed.
- The agent reports what was tested and what remains unverified.
