"""Ratchet (spec-kitty#99): ``patch.dict(sys.modules, ...)`` is banned tree-wide.

``patch.dict`` snapshots the whole target dict at entry and restores it
verbatim on exit (``clear()`` + ``update()``). When the target is
``sys.modules``, any module first-imported *inside* the patched window is
evicted on exit while its parent package keeps the now-stale bound
attribute -- splitting module identity so a later ``from pkg import mod``
resolves the stale parent attribute while a full-path import loads a fresh
object, and a monkeypatch applied to one lands on the other
(spec-kitty#89's root cause; reproduced in
``test_next_command_aborts_before_decide_next_on_failure`` under a
16-worker shard).

The only accepted seam is a single-key ``monkeypatch.setitem(sys.modules,
key, value)``, which restores exactly the one key it touched. #99 converted
the four proven-latent sites (plus one more of the same shape found while
grepping); this gate keeps a sixth site from ever landing again. No
per-owner exemption file: the union of live violations is zero as of #99,
and this gate is the thing that keeps it there.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS: tuple[Path, ...] = (REPO_ROOT / "src", REPO_ROOT / "tests")

#: A detector silently scanning zero files must go red, not pass vacuously.
MIN_SCANNED_FILES = 100


def iter_python_files() -> list[Path]:
    """Every ``.py`` file under ``src/`` and ``tests/``, ``__pycache__`` excluded."""
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def relpath(path: Path) -> str:
    """POSIX-style repo-relative path string for violation messages."""
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _dotted_name(node: ast.AST) -> str | None:
    """Reconstruct a dotted ``Name``/``Attribute`` chain, e.g. ``mock.patch.dict``."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _is_sys_modules_arg(node: ast.AST) -> bool:
    """True for the ``sys.modules`` attribute or the string literal ``"sys.modules"``."""
    if _dotted_name(node) == "sys.modules":
        return True
    return isinstance(node, ast.Constant) and node.value == "sys.modules"


def _patch_dict_sys_modules_linenos(path: Path) -> list[int]:
    """Line numbers of every ``(mock.)patch.dict(sys.modules, ...)`` call in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    linenos: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted_name(node.func)
        if dotted is None or dotted.split(".")[-2:] != ["patch", "dict"]:
            continue
        if node.args and _is_sys_modules_arg(node.args[0]):
            linenos.append(node.lineno)
    return linenos


def collect_violations(paths: list[Path]) -> list[tuple[Path, int]]:
    """``(path, lineno)`` for every banned call site across ``paths``."""
    violations: list[tuple[Path, int]] = []
    for path in paths:
        violations.extend((path, lineno) for lineno in _patch_dict_sys_modules_linenos(path))
    return sorted(violations, key=lambda item: (str(item[0]), item[1]))


def test_scanned_file_floor_is_met() -> None:
    """A detector silently scanning zero files must go red, not green."""
    scanned = iter_python_files()

    assert len(scanned) > MIN_SCANNED_FILES, (
        f"only {len(scanned)} files scanned under {[str(r) for r in SCAN_ROOTS]} -- the patch.dict(sys.modules) ban would otherwise pass vacuously."
    )


def test_no_patch_dict_sys_modules_call_site() -> None:
    """spec-kitty#89/#99: no live ``patch.dict(sys.modules, ...)`` call under src/ or tests/."""
    scanned = iter_python_files()

    violations = collect_violations(scanned)

    assert violations == [], (
        "`patch.dict(sys.modules, ...)` (also `mock.patch.dict(...)`) is banned "
        "(spec-kitty#89/#99): it evicts any module first-imported inside the "
        "patched window when it restores the whole-dict snapshot on exit. Use "
        "`monkeypatch.setitem(sys.modules, key, value)` per key instead.\n"
        "Violations:\n" + "\n".join(f"  {relpath(p)}:{lineno}" for p, lineno in violations)
    )


def test_planted_attribute_form_violation_fires(tmp_path: Path) -> None:
    """A planted ``patch.dict(sys.modules, {...})`` (attribute form) IS caught."""
    module = tmp_path / "offender.py"
    module.write_text(
        "import sys\nfrom unittest.mock import patch\n\nwith patch.dict(sys.modules, {'foo': None}):\n    pass\n",
        encoding="utf-8",
    )

    violations = collect_violations([module])

    assert violations == [(module, 4)]


def test_planted_string_literal_form_violation_fires(tmp_path: Path) -> None:
    """The string-literal spelling ``patch.dict("sys.modules", {...})`` IS also caught."""
    module = tmp_path / "offender.py"
    module.write_text(
        "from unittest.mock import patch\n\nwith patch.dict('sys.modules', {'foo': None}):\n    pass\n",
        encoding="utf-8",
    )

    violations = collect_violations([module])

    assert violations == [(module, 3)]


def test_planted_mock_patch_dict_qualified_form_fires(tmp_path: Path) -> None:
    """The fully-qualified ``mock.patch.dict(sys.modules, ...)`` spelling IS caught too."""
    module = tmp_path / "offender.py"
    module.write_text(
        "import sys\nfrom unittest import mock\n\nwith mock.patch.dict(sys.modules, {'foo': None}):\n    pass\n",
        encoding="utf-8",
    )

    violations = collect_violations([module])

    assert violations == [(module, 4)]


def test_patch_dict_on_a_different_target_is_not_banned(tmp_path: Path) -> None:
    """Only the ``sys.modules`` argument is banned -- ``patch.dict(os.environ, ...)`` is untouched."""
    module = tmp_path / "offender.py"
    module.write_text(
        "import os\nfrom unittest.mock import patch\n\nwith patch.dict(os.environ, {'FOO': 'bar'}):\n    pass\n",
        encoding="utf-8",
    )

    violations = collect_violations([module])

    assert violations == []


def test_setitem_seam_is_not_banned(tmp_path: Path) -> None:
    """The accepted replacement, ``monkeypatch.setitem(sys.modules, ...)``, is never flagged."""
    module = tmp_path / "offender.py"
    module.write_text(
        "import sys\n\n\ndef test_seam(monkeypatch):\n    monkeypatch.setitem(sys.modules, 'foo', None)\n",
        encoding="utf-8",
    )

    violations = collect_violations([module])

    assert violations == []


def test_explanatory_comment_is_not_flagged() -> None:
    """The one sanctioned mention of the banned spelling is prose, invisible to AST scanning."""
    path = REPO_ROOT / "tests" / "specify_cli" / "cli" / "commands" / "test_selector_resolution.py"

    violations = collect_violations([path])

    assert violations == []
