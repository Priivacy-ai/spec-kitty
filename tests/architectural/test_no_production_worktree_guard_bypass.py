"""Architectural guardrail for the mission-creation worktree-context guard.

``create_mission_core(..., allow_worktree_context=True)`` bypasses the
operator-safety guard that refuses to scaffold a mission when the process
``cwd`` resolves inside a git worktree (protecting operators from accidentally
creating a mission inside a lane worktree instead of the project-root
checkout).  The bypass exists solely for programmatic *test* callers -- notably
``tests/_factories.make_mission()`` -- which pass an explicit isolated
``repo_root`` while the test process itself runs from within a lane worktree.

PR #2629 review (architect-alphonso, MEDIUM): the flag is an undefended
public affordance on a core API -- a future *production* caller could set it to
``True`` and silently defeat the operator-safety guard.  This guard pins the
invariant that no ``src/`` call site ever passes ``allow_worktree_context=True``.

If the ``cwd``-vs-target guard is ever reshaped to validate the resolution
target instead (so the flag can be removed entirely), delete this guard with
that change.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_BYPASS_KW = "allow_worktree_context"


def _worktree_bypass_uses(path: Path) -> list[str]:
    """Return call sites in ``path`` that pass ``allow_worktree_context=True``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if (
                kw.arg == _BYPASS_KW
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
            ):
                hits.append(f"{path}:{node.lineno} passes {_BYPASS_KW}=True")
    return hits


def test_no_production_caller_bypasses_worktree_guard() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        offenders.extend(_worktree_bypass_uses(path))

    assert not offenders, (
        "Production code must not bypass the mission-creation worktree-context "
        "guard -- allow_worktree_context=True is reserved for programmatic test "
        "callers (tests/_factories.make_mission). Offending src call sites:\n"
        + "\n".join(offenders)
    )


def test_detector_bites_on_a_planted_bypass(tmp_path: Path) -> None:
    """Non-vacuity: the detector must FLAG a synthetic production bypass.

    Guards against the scanner silently rotting to always-green (e.g. if the
    keyword is renamed and this guard is not co-updated).
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        "create_mission_core(repo_root=root, allow_worktree_context=True)\n",
        encoding="utf-8",
    )
    assert _worktree_bypass_uses(planted), "detector failed to flag a planted bypass"

    # And it must NOT fire on the legitimate default (=False) or absence.
    clean = tmp_path / "clean.py"
    clean.write_text(
        "create_mission_core(repo_root=root, allow_worktree_context=False)\n"
        "create_mission_core(repo_root=root)\n",
        encoding="utf-8",
    )
    assert not _worktree_bypass_uses(clean)
