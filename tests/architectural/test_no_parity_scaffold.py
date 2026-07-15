"""Reappearance guard: no ``*parity_scaffold*`` artifact survives (C-003).

WP03 (resolver-seam-completion) retires the transitional software-dev
byte-parity scaffold that shadowed ``resolve_mission_type_context`` while the
live action-grain union was wired in. Scaffolding of that shape is
explicitly transitional per plan.md C-003 — useful during the swap, but a
liability if left behind: it doubles maintenance on an already-superseded
code path and invites drift between the "real" resolver and its scaffold
double.

This gate is a permanent reappearance guard, not a one-shot cleanup check: it
fails the build the moment any future change (re-)introduces a
``*parity_scaffold*``-named file anywhere under ``src/`` or ``tests/``,
whatever the underlying seam. See
``tests/charter/test_resolved_mission_type_context.py`` for the enduring
determinism assertions the scaffold was standing in for.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_ROOTS: tuple[Path, ...] = (_REPO_ROOT / "src", _REPO_ROOT / "tests")
_PATTERN = "*parity_scaffold*"
#: This guard's own filename intentionally contains "parity_scaffold" (it is
#: the "no parity scaffold" guard, not a scaffold itself) — exclude it, its
#: compiled bytecode, and any ``__pycache__`` noise from the scan.
_SELF_PATH = Path(__file__).resolve()


def _parity_scaffold_paths() -> list[Path]:
    hits: list[Path] = []
    for root in _SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob(_PATTERN)):
            resolved = path.resolve()
            if resolved == _SELF_PATH or "__pycache__" in resolved.parts:
                continue
            hits.append(path)
    return hits


def test_no_parity_scaffold_artifact_survives() -> None:
    offenders = _parity_scaffold_paths()
    assert not offenders, (
        "A transitional '*parity_scaffold*' artifact survived past its WP "
        "(C-003 — scaffolding must be deleted before landing, not left as "
        "permanent duplicate coverage):\n"
        + "\n".join(str(path.relative_to(_REPO_ROOT)) for path in offenders)
    )
