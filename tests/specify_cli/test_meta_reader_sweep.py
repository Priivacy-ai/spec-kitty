"""WP05 / FR-005 (#2100, in-mission scope): the touched-module meta-reader sweep.

FR-005 routes the residual inline ``json.loads(<meta path>.read_text())`` reads in
the modules THIS mission touched — ``mission.py``, ``tasks.py``,
``acceptance/__init__.py`` — through the canonical ``load_meta`` adapter (the WP02-04
integration already re-pointed every meta read in these surfaces; this is the
contract-pin guard that LOCKS the sweep so a future inline read cannot regress in).

The guard is a source/AST scan that proves **zero inline meta reads** remain in the
three touched modules: no ``json.loads(...)`` / ``json.load(...)`` call whose argument
is derived from a ``meta.json`` path's ``.read_text()`` / open. The full ~62-site
backlog beyond these modules stays DEFERRED (Out of Scope, #2100 follow-up) — this
guard is scoped strictly to the touched set so it does not falsely fail on untouched
modules.

Non-vacuity (anti-tautology): the scanner is exercised on a SYNTHETIC snippet that
DOES contain an inline ``json.loads(meta_path.read_text())`` and MUST flag it, and on
a ``load_meta``-routed snippet which MUST pass — WITHOUT depending on the production
source.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOUCHED_MODULES = (
    _REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "agent" / "mission.py",
    _REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "agent" / "tasks.py",
    _REPO_ROOT / "src" / "specify_cli" / "acceptance" / "__init__.py",
)


def _names_in(node: ast.AST) -> set[str]:
    """Collect every identifier appearing inside *node* (names + attribute tails)."""
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            names.add(sub.value)
    return names


def _inline_meta_reads(source: str) -> list[int]:
    """Return line numbers of inline ``json.load(s)`` calls over a meta.json read.

    An inline meta read is a ``json.loads(...)`` / ``json.load(...)`` call whose
    argument subtree references BOTH a file-read primitive (``read_text`` / ``open`` /
    ``read``) AND a ``meta.json`` literal — i.e. the inline pattern the canonical
    ``load_meta`` adapter replaces. A bare ``json.loads(some_arg)`` over an unrelated
    string (e.g. a CLI ``--batch`` payload) is NOT flagged.
    """
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        callee = (
            target.attr
            if isinstance(target, ast.Attribute)
            else target.id
            if isinstance(target, ast.Name)
            else None
        )
        if callee not in {"loads", "load"}:
            continue
        arg_names: set[str] = set()
        for arg in node.args:
            arg_names |= _names_in(arg)
        reads_a_file = bool(arg_names & {"read_text", "open", "read"})
        # The arg subtree references a meta path — either the ``meta.json`` literal
        # directly or a variable whose name carries ``meta`` (``meta_path`` /
        # ``meta_file``), the conventional inline-read shape.
        references_meta = any(
            "meta.json" in name or "meta" in name.lower() for name in arg_names
        )
        if reads_a_file and references_meta:
            hits.append(node.lineno)
    return hits


# ---------------------------------------------------------------------------
# Non-vacuity self-test (anti-tautology) — proven WITHOUT the production source.
# ---------------------------------------------------------------------------

_ROGUE_INLINE_READ = """
import json
def load():
    meta_path = feature_dir / "meta.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))
"""

_CANONICAL_LOAD_META = """
from specify_cli.mission_metadata import load_meta
def load():
    return load_meta(feature_dir)
"""

_UNRELATED_JSON_LOADS = """
import json
def parse(batch):
    return json.loads(batch)
"""


def test_scanner_flags_synthetic_inline_meta_read() -> None:
    """Anti-vacuity: an inline json.loads over a meta.json read IS flagged."""
    assert _inline_meta_reads(_ROGUE_INLINE_READ)


def test_scanner_passes_canonical_load_meta() -> None:
    """Anti-vacuity: the load_meta-routed shape has ZERO inline meta reads."""
    assert _inline_meta_reads(_CANONICAL_LOAD_META) == []


def test_scanner_ignores_unrelated_json_loads() -> None:
    """A json.loads over a non-meta payload (e.g. a CLI batch arg) is NOT flagged."""
    assert _inline_meta_reads(_UNRELATED_JSON_LOADS) == []


# ---------------------------------------------------------------------------
# The production guard: the three touched modules carry NO inline meta read.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_path", _TOUCHED_MODULES, ids=lambda p: p.name)
def test_touched_module_has_no_inline_meta_read(module_path: Path) -> None:
    """FR-005: every meta read in the touched modules routes through ``load_meta``."""
    source = module_path.read_text(encoding="utf-8")
    hits = _inline_meta_reads(source)
    assert hits == [], (
        f"{module_path.name} still has inline json.load(s) meta read(s) at line(s) "
        f"{hits} — route them through the canonical load_meta adapter (FR-005)."
    )
