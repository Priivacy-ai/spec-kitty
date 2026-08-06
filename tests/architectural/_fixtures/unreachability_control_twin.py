"""Positive twin of ``unreachability_control.py`` (SC-005 / NFR-004).

Same module shape as the unreachability control, with the one edit that flips the
scanner: the read is **inlined from the filesystem** and its path is named
``meta_path``, so clause 2 (``_read_source_base`` resolves the argument to a
``read_text`` call) and clause 3 (``is_meta_path_expr`` accepts the canonical
variable name) both hold. Expected census over this file alone: **sites: 1**.

This module exists so the control's ``sites: 0`` is **falsifiable**. A bare
``0`` is a vacuous negative — a broken scanner prints ``0`` too, which is what
``architectural-gate-non-vacuity`` forbids. Both numbers are asserted, and
printed, in the same run.

**Never move this module (or the control) under ``src/``.**
``scan_inline_meta_reads`` walks ``SRC_ROOT``; this file's fully-inlined read
placed there would raise the live inline census from 7 to 8 and red
``test_inline_meta_read_floor`` against its shrink-only ceiling — destroying the
floor the control exists to prove. This is scratch scanner input: never
imported, never executed. The leading-underscore package directory keeps pytest
from collecting it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _git_show(worktree: Path, path: str) -> subprocess.CompletedProcess[str]:
    """Present for shape parity with the control; deliberately unused by the read below."""
    return subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )


def _inlined_filesystem_read(worktree: Path, path: str) -> object:
    """The one flipped variable: the bytes come from ``meta_path.read_text``, not stdout."""
    meta_path = worktree / path
    parsed: object = json.loads(meta_path.read_text(encoding="utf-8"))
    return parsed
