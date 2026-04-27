"""Architectural test: compat/_adapters/ files must contain no logic (WP05).

Each adapter is allowed to contain only:
  - A module docstring (ast.Expr containing ast.Constant)
  - from … import … statements (ast.ImportFrom)
  - import … statements (ast.Import)
  - __all__ = [...] assignment (ast.Assign whose single target is __all__)

Everything else (functions, classes, conditionals, loops, try blocks, any other
assignment) is disallowed and will cause this test to fail with a clear message
naming the offending node type and line number.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_ADAPTERS_DIR = _REPO_ROOT / "src" / "specify_cli" / "compat" / "_adapters"
_FIXTURES_DIR = Path(__file__).parent / "_fixtures"

_ADAPTER_FILES = [
    _ADAPTERS_DIR / "version_checker.py",
    _ADAPTERS_DIR / "gate.py",
    _ADAPTERS_DIR / "detector.py",
]

_DISALLOWED_NODE_TYPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
)


def _is_docstring_node(node: ast.stmt) -> bool:
    """Return True for the module-level docstring expression."""
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _is_all_assignment(node: ast.stmt) -> bool:
    """Return True for ``__all__ = [...]`` (single Name target)."""
    return isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "__all__"


def check_adapter_file(path: Path) -> list[str]:
    """Validate *path* against the no-logic adapter rules.

    Returns a list of violation messages (empty means clean).
    """
    source = path.read_text(encoding="utf-8")
    violations: list[str] = []

    # 1. Marker comment must be present
    if "# adapter:no-logic" not in source:
        violations.append(f"{path.name}: missing '# adapter:no-logic' marker")

    # 2. AST walk — only allowed node types at module body level
    tree = ast.parse(source, filename=str(path))
    for idx, node in enumerate(tree.body):
        # Docstring (first Expr with a string constant) — always allowed
        if idx == 0 and _is_docstring_node(node):
            continue
        # from … import … / import … — allowed
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            continue
        # __all__ = [...] — allowed
        if _is_all_assignment(node):
            continue
        # Any disallowed node type
        if isinstance(node, _DISALLOWED_NODE_TYPES):
            violations.append(f"{path.name}: disallowed node {type(node).__name__} at line {node.lineno}")
            continue
        # Any other Expr (not the docstring) or unexpected assignment
        violations.append(f"{path.name}: unexpected node {type(node).__name__} at line {node.lineno}")

    return violations


# ---------------------------------------------------------------------------
# Parametrised tests for each real adapter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_path", _ADAPTER_FILES, ids=lambda p: p.name)
def test_adapter_no_logic(adapter_path: Path) -> None:
    """Each adapter file must pass the no-logic invariant."""
    assert adapter_path.exists(), f"Adapter file not found: {adapter_path}"
    violations = check_adapter_file(adapter_path)
    assert violations == [], "\n".join(violations)


@pytest.mark.parametrize("adapter_path", _ADAPTER_FILES, ids=lambda p: p.name)
def test_adapter_marker_present(adapter_path: Path) -> None:
    """Each adapter file must contain the '# adapter:no-logic' marker."""
    assert adapter_path.exists(), f"Adapter file not found: {adapter_path}"
    source = adapter_path.read_text(encoding="utf-8")
    assert "# adapter:no-logic" in source, f"{adapter_path.name}: '# adapter:no-logic' marker is absent"


# ---------------------------------------------------------------------------
# Positive test: the checker rejects a known-bad fixture
# ---------------------------------------------------------------------------


def test_bad_adapter_fixture_is_rejected() -> None:
    """The check_adapter_file helper must reject bad_adapter.py (has a def)."""
    bad = _FIXTURES_DIR / "bad_adapter.py"
    assert bad.exists(), f"Fixture not found: {bad}"
    violations = check_adapter_file(bad)
    assert violations, "Expected check_adapter_file to report violations for bad_adapter.py but it returned an empty list — the checker is not working correctly."
    # Confirm the violation names the FunctionDef
    assert any("FunctionDef" in v for v in violations), f"Expected a FunctionDef violation but got: {violations}"
