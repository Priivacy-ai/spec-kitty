"""Shared helper for constructing a real, honestly-skippable EACCES fixture.

Extracted from the pattern ``tests/specify_cli/decisions/test_ownership_3111.py``
established for `#3111`/`#3177` so the same real-permission-bits technique does
not get re-invented (and subtly re-broken — see the docstring below) at each of
the several call sites `#3194` found carrying the same ``Path.is_dir()`` /
``Path.exists()`` / ``Path.is_file()`` EACCES divergence.
"""

from __future__ import annotations

from pathlib import Path


def mode_bits_enforced(probe: Path) -> bool:
    """Return ``True`` when the process is actually denied by *probe*'s mode bits.

    **Skip honestly.** Running as root, or on a filesystem that ignores mode
    bits, makes a ``0o000`` test pass while exercising nothing — the vacuous
    case. *probe* must be a **file** read *after* the directory containing it
    has been ``chmod``'d to ``0o000``: on a directory, opening it always raises
    ``IsADirectoryError`` (itself an ``OSError``), which would make this helper
    constant ``True`` and silently defeat the skip it exists to perform.
    """
    try:
        with probe.open("rb"):
            pass
    except OSError:
        return True
    return False
