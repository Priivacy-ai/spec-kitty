"""Static guard for the path-keyed-cache-fed-a-bare-``tmp_path`` defect class.

Filed by planning#88 — the deferred sweep from [squad] pass 2 on PR #72. That PR fixed the one
live instance (``tests/architectural/_home_pin_scan.py::_corpus``'s caller in
``test_home_pin_scan_limbs.py``) and flagged the defect class for a repo-wide sweep: any
module-level ``@lru_cache`` keyed on a root **path** (never on the root's contents) turns two
pytest items landing on the same physical directory into silent cache poisoning — a later
sibling reads the earlier sibling's parse.

That collision is real under ``tmp_path_retention_policy = failed``: ``_pytest.tmpdir._mk_tmp``
truncates node names at ``MAXVAL = 30`` chars, so parametrizations of one long test name can share
an identical truncated prefix, and once each numbered dir is ``rmtree``'d at its own teardown,
``make_numbered_dir``'s sibling scan restarts numbering and can hand two parametrizations the
SAME physical directory. #72's fix folds the varying parametrize value into a subroot
(``tmp_path / limb_id``) instead of passing the bare fixture — see
``test_home_pin_scan_limbs.py::test_every_inert_sub_form_ships_a_positive_control``.

**What this module checks, mechanically**: every ``@pytest.mark.parametrize``d test function in
``tests/`` that passes the bare ``tmp_path`` fixture (an ``ast.Name`` node, never a subroot
expression such as ``tmp_path / x``) directly as an argument to one of
:data:`PATH_KEYED_CACHE_CONSUMERS` — the functions that resolve through a known path-keyed
``lru_cache`` today. Adding a new such cache means adding its consumer name(s) here.

**What this module deliberately does NOT check**: a truncation collision between two
*non-parametrized* test functions whose names happen to share the same ~30-char prefix. That
variant needs the exact per-node truncated name, which depends on the enclosing module path and
pytest's own numbering state — not reproducible from static AST alone, and no live instance of it
is known. The parametrize case above is the one #72 hit and the one this sweep closes.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

#: Functions that resolve, directly or through a thin wrapper, to a module-level ``lru_cache``
#: keyed on a root PATH argument. Each entry names the cache it reaches so a maintainer can find
#: it. Adding a new path-keyed cache in ``tests/`` means adding its public consumer(s) here.
PATH_KEYED_CACHE_CONSUMERS: frozenset[str] = frozenset(
    {
        "inert_hits",  # tests/architectural/_home_pin_scan.py::_corpus
        "literal_key_occurrences",  # tests/architectural/_home_pin_scan.py::_corpus
        "scan_graph_monolith_paths",  # tests/architectural/_dead_path_scan.py::_text_files
        "scan_shipped_pack_paths",  # tests/architectural/_dead_path_scan.py::_text_files
    }
)

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, order=True)
class Hit:
    """One parametrized test feeding a bare ``tmp_path`` to a path-keyed cache consumer."""

    relpath: str
    lineno: int
    test_name: str
    callee: str


def _is_bare_tmp_path(node: ast.expr) -> bool:
    """``True`` only for the literal fixture name — never a subroot built from it."""
    return isinstance(node, ast.Name) and node.id == "tmp_path"


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_parametrize_decorator(decorator: ast.expr) -> bool:
    return isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "parametrize"


def is_parametrized(node: FunctionNode) -> bool:
    """``True`` when ``node`` carries a ``@pytest.mark.parametrize`` decorator."""
    return any(_is_parametrize_decorator(decorator) for decorator in node.decorator_list)


def scan_module(tree: ast.Module, relpath: str) -> list[Hit]:
    """Every parametrized test in ``tree`` that feeds a bare ``tmp_path`` to a registered consumer."""
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test") or not is_parametrized(node):
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            callee = _callee_name(call.func)
            if callee not in PATH_KEYED_CACHE_CONSUMERS:
                continue
            if any(_is_bare_tmp_path(arg) for arg in call.args):
                hits.append(Hit(relpath, call.lineno, node.name, callee))
    return sorted(hits)


def scan_tree(root: Path) -> list[Hit]:
    """:func:`scan_module` applied to every ``test_*.py`` file under ``root``."""
    hits: list[Hit] = []
    for path in sorted(root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hits.extend(scan_module(tree, path.relative_to(root).as_posix()))
    return sorted(hits)
