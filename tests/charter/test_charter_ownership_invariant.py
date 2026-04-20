"""Charter ownership invariant test.

This test enforces SC-001: exactly one canonical free-function definition of
each registered charter function must exist across all Python files under
``src/``.

Registry update protocol
------------------------
1. **Keep the registry narrow.** ``CANONICAL_OWNERS`` is intentionally limited
   to the two functions named at the time this mission was authored. Do not
   add new entries just because a test starts failing -- that is never the
   right fix.

2. **Adding a name is a per-mission decision.** Expanding ``CANONICAL_OWNERS``
   requires an explicit design decision and a new mission that consciously
   widens the scope of this invariant. Accommodating a failing test by quietly
   adding an entry defeats the purpose of the invariant.

3. **The fix for any failure is always consolidation.** If this test fails it
   means a duplicate definition has appeared somewhere in ``src/``. Remove the
   duplicate and move or redirect the code to the canonical location; never
   add an exception or broaden the allowed set.

4. **Class-attached methods are not counted.** The invariant applies only to
   module-level free functions (``def`` at top level or nested inside other
   functions/conditionals, but NOT methods of a class). If a class defines a
   method named ``build_charter_context`` that is distinct in semantics from
   the canonical free function, it does not count as a duplicate. If this
   invariant ever needs to extend to methods, that is a new contract, not an
   ad-hoc modification to this file.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: AST-walks every .py in the repo (>30s)
pytestmark = pytest.mark.non_sandbox


CANONICAL_OWNERS: dict[str, str] = {
    "build_charter_context": "src/charter/context.py",
    "ensure_charter_bundle_fresh": "src/charter/sync.py",
}


def _find_defs(repo_root: Path, name: str) -> list[Path]:
    """Return repo-relative paths of every Python file under ``src/`` that
    contains a top-level or nested free-function (``FunctionDef`` /
    ``AsyncFunctionDef``) named *name*.

    Class methods with the same name are excluded: only nodes whose immediate
    parent in the AST is NOT a ``ClassDef`` are counted.  In practice this
    is implemented via ``ast.walk`` which visits all nodes; class-body nodes
    appear under ``ClassDef.body`` but ``ast.walk`` has no parent reference.
    Because the invariant contract explicitly excludes class-attached methods,
    we detect them by checking whether any ancestor ``ClassDef`` directly
    contains the function node.
    """
    hits: list[Path] = []
    src_root = repo_root / "src"
    for py in src_root.rglob("*.py"):
        # Exclude generated / cache / worktree paths.
        # Use repo-relative parts so that if the tests themselves are running
        # inside a .worktrees/ checkout the exclusion does not discard every
        # file in src/.
        rel_parts = py.relative_to(repo_root).parts
        if any(part in {"__pycache__", ".worktrees"} for part in rel_parts):
            continue
        try:
            source = py.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py))
        except SyntaxError:
            continue

        # Build a child -> parent mapping so we can detect class methods.
        parent_map: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent_map[child] = node

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != name:
                continue
            # Walk up the parent chain; skip if the immediate parent is a class.
            parent = parent_map.get(node)
            if isinstance(parent, ast.ClassDef):
                continue
            hits.append(py.relative_to(repo_root))

    # Return sorted for deterministic output.
    return sorted(hits)


def test_charter_ownership_invariant(repo_root: Path) -> None:
    """Assert exactly one free-function definition per registered function."""
    violations: list[str] = []

    for fn_name, canonical in CANONICAL_OWNERS.items():
        found = _find_defs(repo_root, fn_name)
        found_strs = [str(p) for p in found]

        if len(found) == 1 and found_strs[0] == canonical:
            # Invariant satisfied.
            continue

        # Build a human-readable violation message.
        lines: list[str] = [
            f"Charter ownership invariant violated for '{fn_name}':",
            f"  canonical location: {canonical}",
            "  definitions found in:",
        ]
        if not found:
            lines.append("    (none — canonical file may be missing or renamed)")
        else:
            for p_str in found_strs:
                tag = "(canonical)" if p_str == canonical else "(DUPLICATE — remove or rename)"
                lines.append(f"    {p_str}  {tag}")

        violations.append("\n".join(lines))

    assert not violations, "\n\n".join(violations)
