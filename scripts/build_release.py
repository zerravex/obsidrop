"""Build the Obsidrop Windows x64 portable release.

The script is intentionally the single build entry point for local use and CI.
It verifies the version metadata, runs PyInstaller in one-folder windowed mode,
checks the executable and bundled Tcl/Tk runtime, stages the portable
distribution, creates the release ZIP, and writes and verifies its SHA-256
checksum.

Run with Python 3.14 on Windows:

    python scripts/build_release.py

On a tagged CI build, pass the tag so the script can reject a mismatch:

    python scripts/build_release.py --tag v0.0.1
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Obsidrop"
BUILD_PYTHON = (3, 14)
PE_MACHINE_AMD64 = 0x8664
PE_SUBSYSTEM_WINDOWS_GUI = 2


class BuildError(RuntimeError):
    """Raised when the release build cannot be completed safely."""


def _read_project_version() -> str:
    pyproject_path = ROOT / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        data = tomllib.load(pyproject_file)

    project = data.get("project")
    if not isinstance(project, dict):
        raise BuildError("pyproject.toml does not contain a [project] table.")

    version = project.get("version")
    if not isinstance(version, str) or not version.strip():
        raise BuildError("pyproject.toml does not define [project].version.")
    return version.strip()


def _read_package_version() -> str:
    init_path = ROOT / "obsidrop" / "__init__.py"
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"Could not read {init_path}: {exc}") from exc

    match = re.search(
        r"""^__version__\s*=\s*["']([^"']+)["']\s*$""",
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        raise BuildError("obsidrop/__init__.py does not define __version__.")
    return match.group(1).strip()


def _validate_versions(tag: str | None) -> str:
    project_version = _read_project_version()
    package_version = _read_package_version()

    if project_version != package_version:
        raise BuildError(
            "Version mismatch: pyproject.toml has "
            f"{project_version!r}, but obsidrop/__init__.py has "
            f"{package_version!r}."
        )

    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", project_version):
        raise BuildError(
            f"Unsupported project version {project_version!r}; expected a "
            "semantic version such as 0.0.1."
        )

    if tag is not None:
        expected_tag = f"v{project_version}"
        if tag != expected_tag:
            raise BuildError(
                f"Tag mismatch: expected {expected_tag}, got {tag}."
            )

    return project_version


def _check_environment() -> None:
    if os.name != "nt":
        raise BuildError("The portable release must be built on Windows.")

    if sys.version_info[:2] != BUILD_PYTHON:
        raise BuildError(
            "The v0.0.1 portable release must be built with Python 3.14; "
            f"this interpreter is {sys.version.split()[0]}."
        )

    if importlib.util.find_spec("PyInstaller") is None:
        raise BuildError(
            "PyInstaller is not installed for this interpreter. Create a "
            "dedicated build environment and install requirements-build.txt."
        )

    if not (ROOT / "app.py").is_file():
        raise BuildError("app.py was not found in the repository root.")

    if not (ROOT / "README-portable.txt").is_file():
        raise BuildError("README-portable.txt was not found.")

    if not (ROOT / "LICENSE").is_file():
        raise BuildError("LICENSE was not found.")


def _run_pyinstaller() -> Path:
    dist_dir = ROOT / "dist"
    app_dir = dist_dir / APP_NAME
    work_dir = ROOT / "build" / "pyinstaller"

    if app_dir.exists():
        shutil.rmtree(app_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        str(ROOT / "app.py"),
    ]
    print("Running PyInstaller:")
    print("  " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    return app_dir


def _read_pe_header(executable: Path) -> tuple[int, int]:
    """Return (machine, subsystem) from a Windows PE executable."""

    try:
        data = executable.read_bytes()
    except OSError as exc:
        raise BuildError(f"Could not read {executable}: {exc}") from exc

    if len(data) < 0x40 or data[:2] != b"MZ":
        raise BuildError(f"{executable.name} is not a valid Windows executable.")

    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise BuildError(f"{executable.name} has an invalid PE header.")

    machine = int.from_bytes(data[pe_offset + 4:pe_offset + 6], "little")
    optional_header = pe_offset + 24
    subsystem = int.from_bytes(
        data[optional_header + 68:optional_header + 70],
        "little",
    )
    return machine, subsystem


def _validate_build(app_dir: Path) -> None:
    executable = app_dir / f"{APP_NAME}.exe"
    internal = app_dir / "_internal"

    if not executable.is_file() or executable.stat().st_size == 0:
        raise BuildError(f"Expected executable was not created: {executable}")

    if not internal.is_dir():
        raise BuildError("PyInstaller did not create the _internal runtime folder.")

    machine, subsystem = _read_pe_header(executable)
    if machine != PE_MACHINE_AMD64:
        raise BuildError(
            "The packaged executable is not x64 "
            f"(PE machine 0x{machine:04X})."
        )
    if subsystem != PE_SUBSYSTEM_WINDOWS_GUI:
        raise BuildError(
            "The packaged executable is not a windowed GUI application "
            f"(PE subsystem {subsystem}). Windows would create a console window."
        )

    python_runtime = list(internal.glob("python3*.dll"))
    if not python_runtime:
        raise BuildError("The bundled Python runtime DLL was not found.")

    tkinter_extension = list(internal.glob("_tkinter*.pyd"))
    if not tkinter_extension:
        raise BuildError("The bundled Tkinter extension was not found.")

    tcl_libraries = [
        path for path in internal.glob("*.dll")
        if path.name.lower().startswith("tcl")
    ]
    tk_libraries = [
        path for path in internal.glob("*.dll")
        if path.name.lower().startswith("tk")
    ]
    if not tcl_libraries:
        raise BuildError("The bundled Tcl runtime library was not found.")
    if not tk_libraries and not any(
        "tk" in path.name.lower() for path in tcl_libraries
    ):
        raise BuildError("The bundled Tk runtime library was not found.")

    tcl_init = list(internal.rglob("init.tcl"))
    tk_init = list(internal.rglob("tk.tcl"))
    if not tcl_init or not tk_init:
        # Tcl/Tk 9 can embed its script library as a ZIP archive in the DLLs.
        embedded_entries: set[str] = set()
        for library in tcl_libraries + tk_libraries:
            try:
                with zipfile.ZipFile(library) as archive:
                    embedded_entries.update(archive.namelist())
            except (OSError, zipfile.BadZipFile):
                continue
        has_tcl_data = any(
            name == "init.tcl" or name.endswith("/init.tcl")
            for name in embedded_entries
        )
        has_tk_data = any(
            name == "tk.tcl" or name.endswith("/tk.tcl")
            for name in embedded_entries
        )
        if not has_tcl_data or not has_tk_data:
            raise BuildError(
                "The bundled Tcl/Tk script library was not found, either as "
                "loose files or embedded in the runtime libraries."
            )

    forbidden = {"tests", "docs", ".git", ".venv", "__pycache__"}
    unexpected = [
        item.name
        for item in app_dir.iterdir()
        if item.name in forbidden
    ]
    if unexpected:
        raise BuildError(
            "Unexpected development files in the build output: "
            + ", ".join(sorted(unexpected))
        )

    print(f"Verified executable: {executable}")
    print(f"Verified PE machine: 0x{machine:04X} (x64)")
    print(f"Verified PE subsystem: {subsystem} (Windows GUI, no console)")
    print(f"Verified Python runtime: {python_runtime[0].name}")
    print(f"Verified Tkinter runtime: {tkinter_extension[0].name}")
    print(
        "Verified Tcl/Tk runtime: "
        + ", ".join(path.name for path in tcl_libraries + tk_libraries)
    )
    if tcl_init and tk_init:
        print(f"Verified Tcl/Tk data: {tcl_init[0].name}, {tk_init[0].name}")
    else:
        print("Verified Tcl/Tk data: embedded in the runtime libraries")


def _stage_distribution(version: str, app_dir: Path) -> tuple[Path, Path, Path]:
    release_dir = ROOT / "release"
    folder_name = f"Obsidrop-{version}-Windows-x64"
    staging_dir = release_dir / folder_name
    zip_path = release_dir / f"Obsidrop-v{version}-Windows-x64.zip"
    checksum_path = zip_path.with_name(zip_path.name + ".sha256")

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    for artifact in (zip_path, checksum_path):
        if artifact.exists():
            artifact.unlink()

    release_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_dir, staging_dir)
    shutil.copyfile(ROOT / "README-portable.txt", staging_dir / "README.txt")
    shutil.copyfile(ROOT / "LICENSE", staging_dir / "LICENSE.txt")

    if not (staging_dir / "README.txt").is_file():
        raise BuildError("The portable README was not copied into the distribution.")
    if not (staging_dir / "LICENSE.txt").is_file():
        raise BuildError("The license was not copied into the distribution.")

    return staging_dir, zip_path, checksum_path


def _create_zip(staging_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.write(staging_dir, staging_dir.name)
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(staging_dir.parent).as_posix(),
                )

    prefix = staging_dir.name + "/"
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()

    if not names:
        raise BuildError("The release ZIP is empty.")
    if any(not name.startswith(prefix) for name in names):
        raise BuildError(
            "The release ZIP contains files outside the expected top-level folder."
        )
    if any(name.startswith(prefix + prefix) for name in names):
        raise BuildError("The release ZIP contains an extra nested top-level folder.")

    required = {
        prefix + f"{APP_NAME}.exe",
        prefix + "README.txt",
        prefix + "LICENSE.txt",
    }
    missing = required.difference(names)
    if missing:
        raise BuildError(
            "The release ZIP is missing required files: "
            + ", ".join(sorted(missing))
        )
    if not any(name.startswith(prefix + "_internal/") for name in names):
        raise BuildError("The release ZIP does not contain the _internal runtime folder.")

    forbidden_prefixes = (
        prefix + "tests/",
        prefix + "docs/",
        prefix + ".git/",
        prefix + ".venv/",
        prefix + "__pycache__/",
    )
    if any(name.startswith(forbidden_prefixes) for name in names):
        raise BuildError("The release ZIP contains development files.")

    print(f"Verified ZIP: {zip_path.name} ({len(names)} entries)")


def _write_checksum(zip_path: Path, checksum_path: Path) -> str:
    digest = hashlib.sha256()
    with zip_path.open("rb") as zip_file:
        for chunk in iter(lambda: zip_file.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = digest.hexdigest()

    with checksum_path.open("w", encoding="utf-8", newline="\n") as checksum_file:
        checksum_file.write(f"{checksum}  {zip_path.name}\n")

    recorded = checksum_path.read_text(encoding="utf-8").strip().split()
    if len(recorded) != 2 or recorded[1] != zip_path.name:
        raise BuildError("The checksum file does not identify the release ZIP.")
    if recorded[0].lower() != checksum:
        raise BuildError("The recorded checksum does not match the release ZIP.")

    verify_digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if verify_digest != checksum:
        raise BuildError("The release ZIP changed after its checksum was written.")

    print(f"Verified SHA-256: {checksum}")
    return checksum


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Obsidrop Windows x64 portable release.",
    )
    parser.add_argument(
        "--tag",
        help="Git tag to validate against the project version (for example v0.0.1).",
    )
    args = parser.parse_args()

    try:
        version = _validate_versions(args.tag)
        _check_environment()
        print(f"Building Obsidrop {version} for Windows x64 with Python {sys.version.split()[0]}.")

        app_dir = _run_pyinstaller()
        _validate_build(app_dir)

        staging_dir, zip_path, checksum_path = _stage_distribution(version, app_dir)
        _create_zip(staging_dir, zip_path)
        checksum = _write_checksum(zip_path, checksum_path)
    except BuildError as exc:
        raise SystemExit(f"Release build failed: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Release build failed: PyInstaller exited with status {exc.returncode}."
        ) from exc

    print()
    print("Release assets:")
    print(f"  {zip_path}")
    print(f"  {checksum_path}")
    print(f"  SHA-256: {checksum}")


if __name__ == "__main__":
    main()
