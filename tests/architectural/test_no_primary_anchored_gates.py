"""Architectural ratchet: ``is_committed()`` stays a single read-surface check (FR-011).

WP01 (Issue #1884) once upgraded ``is_committed()`` to a 3-leg OR taking a
``placement: CommitTarget | None`` (plus ``target_branch`` / ``primary_repo_root``)
so a spec committed only on the coordination branch still satisfied the gate.
WP07 (FR-011) **collapsed** that OR: the sole non-test caller (setup-plan) already
feeds the READ-resolved ``spec_file``, so ``is_committed`` now checks the file
against ``HEAD`` of the git surface it physically lives on — no placement, no
primary-target-branch leg. The read surface converges with the retired OR on
every reachable cell (the #1848 coord-deleted case never reaches the check; the
read path raises ``CoordinationBranchDeleted`` upstream).

This ratchet now pins the *post-collapse* contract — re-introducing the
topology parameters (re-expanding the OR rather than trusting the read seam) is
the regression:

1. The ``is_committed`` signature MUST NOT re-add ``placement`` /
   ``target_branch`` / ``primary_repo_root`` parameters.
2. No call site in ``src/`` may pass those keywords.

A change that re-adds any of those parameters fails this test, forcing a
deliberate decision to re-expand the collapsed surface.

WP07 / FR-011 (supersedes the WP01 / #1884 ``placement=``-required ratchet).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_SUBSTANTIVE = _SRC_ROOT / "specify_cli" / "missions" / "_substantive.py"

# Parameters retired by the FR-011 collapse. Their reappearance on the
# ``is_committed`` signature (or at a call site) re-expands the OR.
_RETIRED_PARAMS: frozenset[str] = frozenset(
    {"placement", "target_branch", "primary_repo_root"}
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _is_committed_signature_params(path: Path) -> set[str]:
    """Return the parameter names of the ``is_committed`` def in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "is_committed":
            args = node.args
            names: set[str] = set()
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                names.add(arg.arg)
            if args.vararg:
                names.add(args.vararg.arg)
            if args.kwarg:
                names.add(args.kwarg.arg)
            return names
    raise AssertionError(f"is_committed not found in {_rel(path)}")


def _find_retired_kwarg_calls(path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, kwarg)`` for ``is_committed(...)`` calls using a retired param."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "is_committed"):
            continue
        for kw in node.keywords:
            if kw.arg in _RETIRED_PARAMS:
                violations.append((node.lineno, kw.arg or "<unknown>"))
    return violations


def test_is_committed_signature_has_no_retired_topology_params() -> None:
    """The collapsed ``is_committed`` must not re-add the retired OR parameters."""
    params = _is_committed_signature_params(_SUBSTANTIVE)
    re_added = params & _RETIRED_PARAMS
    assert not re_added, (
        "is_committed re-added retired topology parameter(s) "
        f"{sorted(re_added)} — FR-011 collapsed the 3-leg OR to a single "
        "read-surface HEAD check. Feed the read-resolved spec_file instead of "
        "re-expanding the surface."
    )


def test_no_is_committed_call_passes_retired_topology_kwargs() -> None:
    """No call site in ``src/`` may pass the retired topology keywords."""
    violations: dict[str, list[tuple[int, str]]] = {}

    for py_file in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        lines = _find_retired_kwarg_calls(py_file)
        if lines:
            violations[_rel(py_file)] = lines

    if violations:
        details = "\n".join(
            f"  {path}: {entries}" for path, entries in sorted(violations.items())
        )
        pytest.fail(
            "Found is_committed() calls passing a retired topology keyword "
            "(placement / target_branch / primary_repo_root).\n"
            "FR-011 collapsed the OR to a single read-surface check — pass only "
            "the read-resolved file + repo_root.\n\n"
            f"Violations:\n{details}"
        )
