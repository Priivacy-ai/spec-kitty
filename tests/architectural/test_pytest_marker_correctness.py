"""Architectural convention: pytest markers must be applied *correctly*.

The sister convention test ``test_pytest_marker_convention.py`` enforces
**presence** of a module-level ``pytestmark``. This file enforces **correctness**
of specific markers whose intent can be verified statically from test source.

Rules pinned here
-----------------

**Rule 1 — git_repo presence.** A test file that calls ``git`` via
``subprocess`` (the only legitimate way to drive real git from a test)
MUST carry the ``git_repo`` marker. The marker is the project's signal
that the test creates a real git repository and depends on the host's
git binary; CI uses ``-m git_repo`` to isolate git-plumbing breakage.

**Rule 2 — fast exclusion of subprocess users.** A test file that uses
``subprocess`` (any callable: ``run``, ``Popen``, ``check_call``,
``check_output``, ``call``) MUST NOT carry the ``fast`` marker. The
``fast`` marker promises sub-second pure-logic execution with no
subprocess fan-out; a subprocess-spawning test in the ``fast`` lane
poisons the inner developer loop. See ``docs/context/testing-taxonomy.md``
under "Fast" for the canonical definition.

What this file does NOT enforce
-------------------------------

- It does not enforce that an ``integration`` test really uses I/O
  (hard to detect statically without false positives on `tmp_path` usage).
- It does not enforce that a ``slow`` test really takes >10 seconds
  (only wall-clock can measure that).
- It does not enforce one-category-per-file mutual exclusion (some
  files legitimately layer multiple category markers; we may revisit).
- It does not enforce that a ``live_adapter`` test really hits a live API
  (would require differentiating real vs mocked client construction).

Why these two rules
-------------------

They have the lowest false-positive risk and the highest signal-to-noise.
``subprocess`` is unambiguous when scanned via AST — the call expression
``subprocess.run("git" / ["git", ...])`` is a clear and verifiable
intent to invoke real git, and the ``fast`` lane's contract is broken
in measurable ways by even a single subprocess call.

If a test is wrongly flagged by either rule, the answer is almost
always to update the marker (the marker was wrong) rather than to add
an exception to this convention.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


pytestmark = [pytest.mark.architectural]


_TESTS_ROOT = Path(__file__).resolve().parents[1]
_SELF = Path(__file__).resolve()
_SISTER = _TESTS_ROOT / "architectural" / "test_pytest_marker_convention.py"

_SUBPROCESS_CALLABLES: frozenset[str] = frozenset(
    {"run", "Popen", "check_call", "check_output", "call"}
)


def _iter_test_files() -> list[Path]:
    paths: list[Path] = []
    for path in _TESTS_ROOT.rglob("test_*.py"):
        if path.resolve() in {_SELF, _SISTER.resolve()}:
            continue
        if any(part.startswith((".", "__")) for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


def _collect_markers(tree: ast.Module) -> set[str]:
    """Return every marker name carried by the module's `pytestmark` assignment.

    Handles list form (``pytestmark = [pytest.mark.foo, pytest.mark.bar]``)
    and singleton form (``pytestmark = pytest.mark.foo``). Markers applied
    only via decorators on individual tests are NOT collected here — the
    rule we enforce is at module level, by design.
    """
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            continue
        value = node.value
        candidates = value.elts if isinstance(value, (ast.List, ast.Tuple)) else [value]
        for expr in candidates:
            # The marker reference is either `pytest.mark.<name>` or a
            # call expression `pytest.mark.<name>(arg)`. Both are Attribute
            # access where the .attr is the marker name and the value chain
            # leads to `pytest.mark`.
            target = expr.func if isinstance(expr, ast.Call) else expr
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr == "mark"
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "pytest"
            ):
                names.add(target.attr)
    return names


def _file_invokes_subprocess(tree: ast.Module) -> bool:
    """True iff the module contains a `subprocess.<callable>(...)` call.

    We walk the full AST (not just top-level) because subprocess calls
    typically live inside fixtures and helper functions. We match by
    callable name (`run`, `Popen`, ...) anchored to a `subprocess` attribute
    chain, so an unrelated identifier named `run` does not false-positive.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in _SUBPROCESS_CALLABLES
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            return True
    return False


_GIT_STRING_RE = re.compile(r'(["\'])git\1')


def _file_invokes_git_via_subprocess(tree: ast.Module, source: str) -> bool:
    """True iff the module both invokes subprocess AND references "git" as a literal string.

    The ``"git"`` literal is the universal first argument when driving the
    git binary. We require BOTH a subprocess call and a ``"git"`` literal
    in the file to reduce false positives (e.g., a file that uses
    subprocess to call a different tool but mentions git in a docstring).
    """
    if not _file_invokes_subprocess(tree):
        return False
    return bool(_GIT_STRING_RE.search(source))


def _format_rule_violations(
    rule_label: str,
    violators: list[Path],
    fix_hint: str,
) -> str:
    rel = [str(p.relative_to(_TESTS_ROOT.parent)) for p in violators]
    bullet_list = "\n  - ".join(rel)
    return (
        f"\n{rule_label}\n"
        f"  - {bullet_list}\n"
        f"\nFix: {fix_hint}\n"
    )


def test_subprocess_git_users_must_carry_git_repo_marker() -> None:
    """Rule 1: a test file that calls ``git`` via ``subprocess`` MUST be tagged ``git_repo``."""
    violators: list[Path] = []
    for path in _iter_test_files():
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        if not _file_invokes_git_via_subprocess(tree, source):
            continue
        markers = _collect_markers(tree)
        if "git_repo" not in markers:
            violators.append(path)

    assert not violators, _format_rule_violations(
        "Marker correctness — Rule 1 (git_repo presence). The following test files "
        "invoke `git` via `subprocess` but do NOT carry the `git_repo` marker, which "
        "means CI's `-m git_repo` filter will silently skip them:",
        violators,
        "add `git_repo` to the file's `pytestmark` list (alongside the existing "
        "category marker), e.g. `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`. "
        "See docs/context/testing-taxonomy.md → 'Git Repo'.",
    )


def test_fast_marker_must_not_apply_to_subprocess_users() -> None:
    """Rule 2: a test file that uses ``subprocess`` MUST NOT be tagged ``fast``."""
    violators: list[Path] = []
    for path in _iter_test_files():
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        if not _file_invokes_subprocess(tree):
            continue
        markers = _collect_markers(tree)
        if "fast" in markers:
            violators.append(path)

    assert not violators, _format_rule_violations(
        "Marker correctness — Rule 2 (fast excludes subprocess). The following test "
        "files carry the `fast` marker but invoke `subprocess.<callable>` — they "
        "poison the inner developer loop's `-m fast` profile by inflating its "
        "wall-clock with subprocess work:",
        violators,
        "remove `pytest.mark.fast` from the file's `pytestmark` list. If the test "
        "is genuinely fast despite using subprocess (e.g. it spawns a trivial process "
        "once), prove it with a wall-clock measurement and split the file so the "
        "fast portion lives alone. See docs/context/testing-taxonomy.md → 'Fast'.",
    )
