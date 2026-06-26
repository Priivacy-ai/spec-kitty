"""Single-definition assertion for the RETROSPECTIVE_FILENAME constant (FR-010 / T064).

SC-006(a): exactly one named constant defines "retrospective.yaml"; no bare
path-composition literal survives in the six .py files that were hoisted.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Structural/source-inspection guard (single-definition constant + AST literal
# scan). Selected by the `misc` integration shard's
# `(git_repo or integration or architectural)` marker expr — without a gated
# marker this file runs in ZERO CI gates (gate-coverage orphan ratchet).
pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# T064-a — constant is importable and has the correct value
# ---------------------------------------------------------------------------


def test_retrospective_filename_constant_value() -> None:
    """RETROSPECTIVE_FILENAME equals 'retrospective.yaml' and is importable."""
    from specify_cli.core.constants import RETROSPECTIVE_FILENAME  # noqa: PLC0415

    assert RETROSPECTIVE_FILENAME == "retrospective.yaml"


def test_retrospective_filename_in_all() -> None:
    """RETROSPECTIVE_FILENAME is declared in __all__ of core.constants."""
    import specify_cli.core.constants as mod  # noqa: PLC0415

    assert "RETROSPECTIVE_FILENAME" in mod.__all__


# ---------------------------------------------------------------------------
# T064-b — no bare path-composition literal survives in the hoisted modules
# ---------------------------------------------------------------------------

#: The six .py files that were identified as hoistable-literal sites.
_HOISTED_MODULES: tuple[str, ...] = (
    "src/specify_cli/retrospective/writer.py",
    "src/specify_cli/retrospective/lifecycle_events.py",
    "src/specify_cli/retrospective/summary.py",
    "src/specify_cli/cli/commands/retrospect.py",
    "src/specify_cli/post_merge/retrospective_terminus.py",
    "src/runtime/next/_internal_runtime/retrospective_terminus.py",
)

_TARGET_LITERAL = "retrospective.yaml"


def _contains_bare_literal(source: str) -> bool:
    """Return True if *source* contains a bare "retrospective.yaml" string literal.

    "Bare" means it appears as a code string constant — not inside a comment or
    docstring.  We walk the AST and collect all Constant nodes; if any equals
    the target, a bare literal survives.

    Docstrings are AST Constant nodes attached as the first expression of a
    module/class/function body.  We collect those positions and exclude them so
    only real code literals are flagged.
    """
    tree = ast.parse(source)

    # Collect line numbers of docstring nodes (safe to ignore).
    docstring_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstring_lines.add(body[0].value.lineno)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value == _TARGET_LITERAL
            and node.lineno not in docstring_lines
        ):
            return True
    return False


def test_no_bare_literal_in_hoisted_modules() -> None:
    """No bare 'retrospective.yaml' path literal survives in the hoisted modules.

    This is a count-agnostic guard: any surviving code literal fails the test.
    Docstrings and comments (which are stripped by the AST parser) are excluded.
    """
    # Resolve the project root as the parent of 'src/'.
    # This test file lives at tests/core/test_retrospective_filename_constant.py.
    repo_root = Path(__file__).parent.parent.parent

    survivors: list[str] = []
    for rel_path in _HOISTED_MODULES:
        module_path = repo_root / rel_path
        if not module_path.exists():
            # File absent (e.g. runtime package not in this checkout) — skip.
            continue
        source = module_path.read_text(encoding="utf-8")
        if _contains_bare_literal(source):
            survivors.append(rel_path)

    assert not survivors, (
        f"Bare 'retrospective.yaml' code literal survives in: {survivors!r}. "
        "Replace with `RETROSPECTIVE_FILENAME` from `specify_cli.core.constants`."
    )
