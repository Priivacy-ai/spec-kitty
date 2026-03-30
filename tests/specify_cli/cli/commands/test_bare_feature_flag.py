"""Regression guard: no bare (undeprecated) ``--feature`` flags in CLI modules.

Canon terminology: "Mission" is canonical; "--feature" is a deprecated alias
that must always be declared ``hidden=True`` in Typer commands and must always
carry ``"[Deprecated] Use --mission"`` in its help text.

Any CLI option that registers ``--feature`` without ``hidden=True`` is a
terminology-consistency violation that this test will catch at commit time.

Scope
-----
- All ``src/specify_cli/cli/`` Typer command modules.
- ``src/specify_cli/orchestrator_api/commands.py`` (orchestrator API surface).
- ``src/specify_cli/scripts/tasks/tasks_cli.py`` (argparse surface).

What is allowed (will NOT fail this test)
------------------------------------------
- ``typer.Option(None, "--feature", hidden=True, ...)``
- ``typer.Option(None, "--feature", hidden=True, help="[Deprecated] ...")``
- argparse ``add_argument("--feature", dest="mission", ...)``

What is NOT allowed (will fail this test)
------------------------------------------
- ``typer.Option(..., "--feature", help="Feature slug")``      # no hidden=True
- ``add_argument("--feature", help="...")``                     # no dest="mission"
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[4]
_SRC = _REPO_ROOT / "src" / "specify_cli"

# Typer-based modules to scan (all .py under cli/ + orchestrator_api/commands.py)
_TYPER_MODULES: list[Path] = sorted(
    list((_SRC / "cli").rglob("*.py")) + [_SRC / "orchestrator_api" / "commands.py"],
)

# Argparse-based modules to scan
_ARGPARSE_MODULES: list[Path] = [
    _SRC / "scripts" / "tasks" / "tasks_cli.py",
]


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _is_hidden_true(keywords: list[ast.keyword]) -> bool:
    """Return True if ``hidden=True`` appears in the keyword list."""
    for kw in keywords:
        if kw.arg == "hidden" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def _has_argparse_dest_mission(keywords: list[ast.keyword]) -> bool:
    """Return True if ``dest='mission'`` appears in the keyword list."""
    for kw in keywords:
        if kw.arg == "dest" and isinstance(kw.value, ast.Constant) and kw.value.value == "mission":
            return True
    return False


def _extract_string_args(call: ast.Call) -> list[str]:
    """Return the string positional arguments of a Call node."""
    return [arg.value for arg in call.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]


# ---------------------------------------------------------------------------
# Scanner: Typer
# ---------------------------------------------------------------------------


class _TyperFeatureFlagVisitor(ast.NodeVisitor):
    """Collect ``typer.Option(...)`` / ``typer.Argument(...)`` calls that use
    ``"--feature"`` without ``hidden=True``."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        # Match typer.Option(...) and typer.Argument(...)
        is_typer_call = (
            isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "typer" and func.attr in ("Option", "Argument")
        )
        if is_typer_call:
            str_args = _extract_string_args(node)
            if "--feature" in str_args and not _is_hidden_true(node.keywords):
                snippet = ast.unparse(node)
                self.violations.append((node.lineno, snippet))
        self.generic_visit(node)


def _scan_typer_module(path: Path) -> list[tuple[Path, int, str]]:
    """Return (path, lineno, snippet) for each bare --feature in a Typer module."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    visitor = _TyperFeatureFlagVisitor(path)
    visitor.visit(tree)
    return [(path, lineno, snippet) for lineno, snippet in visitor.violations]


# ---------------------------------------------------------------------------
# Scanner: argparse
# ---------------------------------------------------------------------------


class _ArgparseFeatureFlagVisitor(ast.NodeVisitor):
    """Collect ``add_argument("--feature", ...)`` calls that don't have
    ``dest="mission"``."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        is_add_argument = isinstance(func, ast.Attribute) and func.attr == "add_argument"
        if is_add_argument:
            str_args = _extract_string_args(node)
            if "--feature" in str_args and not _has_argparse_dest_mission(node.keywords):
                snippet = ast.unparse(node)
                self.violations.append((node.lineno, snippet))
        self.generic_visit(node)


def _scan_argparse_module(path: Path) -> list[tuple[Path, int, str]]:
    """Return (path, lineno, snippet) for each bare --feature in an argparse module."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    visitor = _ArgparseFeatureFlagVisitor(path)
    visitor.visit(tree)
    return [(path, lineno, snippet) for lineno, snippet in visitor.violations]


# ---------------------------------------------------------------------------
# Collect all violations
# ---------------------------------------------------------------------------


def _all_violations() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for module in _TYPER_MODULES:
        if module.exists():
            violations.extend(_scan_typer_module(module))
    for module in _ARGPARSE_MODULES:
        if module.exists():
            violations.extend(_scan_argparse_module(module))
    return violations


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------


def _violation_id(v: tuple[Path, int, str]) -> str:
    path, lineno, _ = v
    rel = path.relative_to(_REPO_ROOT)
    return f"{rel}:{lineno}"


_VIOLATIONS = _all_violations()


@pytest.mark.parametrize("violation", _VIOLATIONS, ids=_violation_id)
def test_no_bare_feature_flag(violation: tuple[Path, int, str]) -> None:
    """Every --feature option must be hidden=True (Typer) or dest='mission' (argparse)."""
    path, lineno, snippet = violation
    rel = path.relative_to(_REPO_ROOT)
    msg = textwrap.dedent(f"""
        Bare (undeprecated) --feature flag found in {rel}:{lineno}

        Snippet: {snippet}

        Fix: add hidden=True and change help to "[Deprecated] Use --mission"
             for Typer options; or add dest="mission" for argparse arguments.

        See: architecture/2.x/04_implementation_mapping/README.md — Canon terminology.
    """).strip()
    pytest.fail(msg)


def test_no_bare_feature_flags_summary() -> None:
    """Aggregate guard: fails if ANY bare --feature flag exists in the codebase.

    This single test always runs (unlike the parametrised one which only
    generates test cases for existing violations).  It provides a clear
    summary when violations are present.
    """
    if not _VIOLATIONS:
        return  # all clean

    lines = ["Bare --feature flags detected (must add hidden=True / dest='mission'):"]
    for path, lineno, snippet in _VIOLATIONS:
        rel = path.relative_to(_REPO_ROOT)
        lines.append(f"  {rel}:{lineno}  →  {snippet[:120]}")
    pytest.fail("\n".join(lines))
