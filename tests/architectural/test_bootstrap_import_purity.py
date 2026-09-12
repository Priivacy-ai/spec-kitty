"""C-LDR-6: ``specify_cli.bootstrap.env_file``'s transitive import set is
stdlib + ``kernel`` only (WP02 T010).

The loader is invoked as the FIRST statements of ``specify_cli/__init__.py``
-- before any other spec-kitty submodule is imported (C-LDR-2) and before
the NFR-001 startup budget can absorb any extra cost. Two invariants pin
that:

1. Every import statement reachable by following the loader's own imports
   (transitively, through ``kernel.*`` and ``specify_cli.bootstrap.*``/
   ``specify_cli.core.env`` only -- the one explicitly-permitted exception,
   see the loader module's own docstring for why it is unused today) is
   either stdlib or one of those two roots. In particular this forbids
   ``specify_cli.core`` (bare), whose package ``__init__`` unconditionally
   imports a wide slice of the CLI (see
   ``src/specify_cli/bootstrap/env_file.py``'s module docstring).
2. None of those reachable modules performs a module-level (import-time,
   i.e. outside any function/class body) ``os.environ``/``os.getenv``
   access -- the loader's whole job is to seed ``os.environ`` BEFORE
   anything else reads decision-relevant vars from it; a transitively
   imported module reading it at its own import time would race the
   loader's own ordering guarantee.

Both checks walk actual import statements via ``ast``, not string/vocabulary
matching (contrast ``test_kernel_env_expand_no_upward_import.py``, which
scans for *forbidden* vocabulary in a small trusted module) -- the seam here
protects an *allow-list*, appropriate for a module with a live NFR-001
performance budget.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_ENTRY_MODULE = "specify_cli.bootstrap.env_file"

#: Python's own stdlib module-name registry (3.10+; this repo targets 3.11+).
_STDLIB_ROOTS = frozenset(sys.stdlib_module_names) | {"__future__"}

#: The only non-stdlib import roots the loader (and anything it transitively
#: imports) may reference. ``specify_cli.core.env`` is the one documented
#: exception from the WP task text (side-effect-free truthy grammar) -- see
#: ``src/specify_cli/bootstrap/env_file.py``'s module docstring for why the
#: loader itself does not currently use it. Bare ``specify_cli.core`` (or any
#: other ``specify_cli.*`` surface) is NOT in this list.
_ALLOWED_NON_STDLIB_PREFIXES = ("kernel", "specify_cli.bootstrap", "specify_cli.core.env")

#: Roots that are followed transitively (i.e. we also scan what THEY import).
#: stdlib modules are trusted wholesale and never walked into.
_WALKABLE_ROOTS = ("kernel", "specify_cli.bootstrap", "specify_cli.core.env")


def _is_allowed_root(module: str) -> bool:
    root = module.split(".", 1)[0]
    if root in _STDLIB_ROOTS:
        return True
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in _ALLOWED_NON_STDLIB_PREFIXES)


def _is_walkable(module: str) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in _WALKABLE_ROOTS)


def _module_file(module: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None or not spec.origin.endswith(".py"):
        return None
    return Path(spec.origin)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _top_level_import_targets(tree: ast.Module) -> list[str]:
    """Import targets from TOP-LEVEL statements only (import-time scope).

    A ``from x import y`` inside a function body only executes when that
    function is *called* -- not at module-import time -- so it is
    deliberately excluded here (mirrors how ``kernel/paths.py`` itself
    defers its one ``platformdirs`` import into a function body precisely
    to keep it out of module-import cost).
    """
    targets: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            targets.append(node.module)
    return targets


def _module_level_environ_access_lines(tree: ast.Module) -> list[int]:
    """Line numbers of top-level ``os.environ``/``os.getenv`` access.

    Only descends into statements that execute at import time -- function
    and class bodies are skipped, matching the "import-time" scope of
    C-LDR-6.
    """
    hits: list[int] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        for sub in ast.walk(node):
            # Deliberately if/elif, not a combined `or` condition (ruff SIM114):
            # each branch's isinstance() check is what lets mypy narrow `sub`'s
            # type enough to see `.lineno` -- a combined boolean condition loses
            # that narrowing (ast.AST itself declares no `.lineno`).
            if isinstance(sub, ast.Attribute) and sub.attr == "environ":  # noqa: SIM114
                hits.append(sub.lineno)
            elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "getenv":
                hits.append(sub.lineno)
    return hits


def _walk_transitive(entry: str) -> dict[str, Path]:
    """BFS from ``entry`` through its own (allowed, walkable) import targets."""
    visited: dict[str, Path] = {}
    queue = [entry]
    while queue:
        module = queue.pop()
        if module in visited:
            continue
        path = _module_file(module)
        if path is None:
            continue
        visited[module] = path
        for target in _top_level_import_targets(_parse(path)):
            if _is_walkable(target) and target not in visited:
                queue.append(target)
    return visited


def test_entry_module_exists_and_is_scanned() -> None:
    """Non-vacuity: the loader module is real and resolvable."""
    path = _module_file(_ENTRY_MODULE)
    assert path is not None and path.is_file()


def test_walk_reaches_more_than_the_entry_module() -> None:
    """Non-vacuity: the transitive walk actually follows into kernel.*.

    Pins that this test would catch a regression where the loader stopped
    importing anything from ``kernel`` at all (which would make both
    invariant checks below vacuously pass).
    """
    visited = _walk_transitive(_ENTRY_MODULE)
    assert _ENTRY_MODULE in visited
    kernel_modules = [m for m in visited if m.split(".", 1)[0] == "kernel"]
    assert kernel_modules, f"expected at least one kernel.* module reachable from {_ENTRY_MODULE}, got {sorted(visited)}"


def test_transitive_imports_are_stdlib_kernel_or_core_env_only() -> None:
    """C-LDR-6: every import reachable from the loader is stdlib + kernel (+ core.env)."""
    visited = _walk_transitive(_ENTRY_MODULE)
    violations: list[tuple[str, str]] = []
    for module, path in visited.items():
        for target in _top_level_import_targets(_parse(path)):
            if not _is_allowed_root(target):
                violations.append((module, target))

    assert violations == [], (
        f"disallowed import(s) reachable from {_ENTRY_MODULE} (allowed: stdlib, "
        f"{_ALLOWED_NON_STDLIB_PREFIXES}):\n"
        + "\n".join(f"  {module} imports {target!r}" for module, target in violations)
    )


def test_no_transitively_reachable_module_reads_os_environ_at_import_time() -> None:
    """C-LDR-6: no module reachable from the loader reads os.environ at import time.

    The loader's whole purpose is to seed ``os.environ`` before anything
    downstream makes a decision from it -- a transitively imported module
    reading ``os.environ``/``os.getenv`` at its OWN import time would race
    that guarantee.
    """
    visited = _walk_transitive(_ENTRY_MODULE)
    violations: list[tuple[str, int]] = []
    for module, path in visited.items():
        for lineno in _module_level_environ_access_lines(_parse(path)):
            violations.append((module, lineno))

    assert violations == [], (
        f"import-time os.environ/os.getenv access reachable from {_ENTRY_MODULE}:\n"
        + "\n".join(f"  {module}:{lineno}" for module, lineno in violations)
    )
