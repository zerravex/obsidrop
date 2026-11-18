"""Shared helpers for filesystem tests."""

from __future__ import annotations

import os
import unittest
from pathlib import Path


def create_directory_link(link: Path, target: Path) -> None:
    """Create a symlink, or a Windows junction when symlinks are unavailable."""

    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass

    if os.name == "nt":
        try:
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
            return
        except (OSError, ImportError, AttributeError):
            pass

    raise unittest.SkipTest("Directory symlinks and junctions are unavailable on this system.")


def remove_directory_link(link: Path) -> None:
    """Remove a directory symlink or junction without deleting its target."""

    if not os.path.lexists(link):
        return
    try:
        os.rmdir(link)
    except OSError:
        try:
            link.unlink()
        except OSError:
            pass
