"""Architectural test: no new prompt-builder filtering call sites (C-011).

This test walks ``src/specify_cli/`` and asserts that no new call sites have
been introduced that filter prompt-builder context.  Filtering prompt-builder
context is prohibited by C-011 (spec.md).

What we look for:
  - Function definitions matching: ``filter_urns``, ``redact_urns``,
    ``exclude_urns``, ``hide_artifacts``, ``filter_context``, ``redact_context``,
    ``exclude_context``, ``filter_prompt``, ``redact_prompt``, ``hide_prompt``
  - Argument names matching: ``exclude_urns``, ``hide_artifacts``,
    ``filter_context``, ``redact_urns``
  - We do NOT flag general-purpose ``filter_*`` helpers that operate on
    frontmatter, severity levels, or runtime-state paths (those are unrelated
    to prompt-builder context and are grandfathered below).

Grandfathered sites (pre-existing, unrelated to prompt-builder context):
  These sites use ``filter_`` in a non-prompt-builder context and are NOT
  violations of C-011.  They are listed here for transparency; the test
  does not count them.

  - src/specify_cli/charter_lint/findings.py:
      ``filter_by_severity`` — filters charter-lint findings by severity level
  - src/specify_cli/charter_lint/engine.py:
      ``report.filter_by_severity(...)`` — caller of the above
  - src/specify_cli/template/asset_generator.py:
      ``_filter_frontmatter`` — strips template frontmatter before rendering
  - src/specify_cli/cli/commands/agent/tasks.py:
      ``_filter_runtime_state_paths`` — cleans git-porcelain output

The test fails on ANY NEW site that matches the prompt-builder filtering
patterns above, regardless of whether it appears alongside one of the
grandfathered sites.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).parent.parent.parent / "src" / "specify_cli"

# Patterns that indicate prompt-builder context filtering (C-011 violations)
_PROMPT_FILTER_FUNCNAMES: frozenset[str] = frozenset({
    "filter_urns",
    "redact_urns",
    "exclude_urns",
    "hide_artifacts",
    "filter_context",
    "redact_context",
    "exclude_context",
    "filter_prompt",
    "redact_prompt",
    "hide_prompt",
    "filter_scope",
    "redact_scope",
    "exclude_scope",
})

# Argument names that indicate prompt-builder filtering
_PROMPT_FILTER_ARGNAMES: frozenset[str] = frozenset({
    "exclude_urns",
    "hide_artifacts",
    "filter_context",
    "redact_urns",
    "filter_scope",
})

# ---------------------------------------------------------------------------
# Grandfathered sites (pre-existing, NOT prompt-builder violations)
# Key: (relative_path_from_src_specify_cli, function_or_variable_name)
# ---------------------------------------------------------------------------
_GRANDFATHERED: frozenset[tuple[str, str]] = frozenset({
    ("charter_lint/findings.py", "filter_by_severity"),
    ("charter_lint/engine.py", "filter_by_severity"),
    ("template/asset_generator.py", "_filter_frontmatter"),
    ("cli/commands/agent/tasks.py", "_filter_runtime_state_paths"),
})


# ---------------------------------------------------------------------------
# AST scanner
# ---------------------------------------------------------------------------


def _find_prompt_filter_sites(root: Path) -> list[tuple[str, int, str]]:
    """Return list of (rel_path, lineno, description) for new violations."""
    violations: list[tuple[str, int, str]] = []

    for py_file in sorted(root.rglob("*.py")):
        rel_path = py_file.relative_to(root).as_posix()

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            # Check function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if name in _PROMPT_FILTER_FUNCNAMES:
                    key = (rel_path, name)
                    if key not in _GRANDFATHERED:
                        violations.append((rel_path, node.lineno, f"function def: {name}"))

                # Check argument names
                all_args = [
                    a.arg
                    for a in (
                        node.args.args
                        + node.args.posonlyargs
                        + node.args.kwonlyargs
                        + ([node.args.vararg] if node.args.vararg else [])
                        + ([node.args.kwarg] if node.args.kwarg else [])
                    )
                ]
                for arg in all_args:
                    if arg in _PROMPT_FILTER_ARGNAMES:
                        key = (rel_path, arg)
                        if key not in _GRANDFATHERED:
                            violations.append(
                                (rel_path, node.lineno, f"argument '{arg}' in {name}")
                            )

    return violations


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_no_new_prompt_filter_call_sites() -> None:
    """No new prompt-builder filtering call sites under src/specify_cli/.

    If this test fails, a new C-011-violating site has been introduced.
    Check the violation list and either:
      a) Remove the filtering (preferred), or
      b) If the function is genuinely unrelated to prompt-builder context,
         add it to _GRANDFATHERED with a justification comment.
    """
    violations = _find_prompt_filter_sites(_SRC_ROOT)

    if violations:
        lines = "\n".join(
            f"  {path}:{lineno}: {desc}"
            for path, lineno, desc in violations
        )
        raise AssertionError(
            f"Found {len(violations)} new prompt-builder filtering call site(s) "
            f"(C-011 violation):\n{lines}\n\n"
            "Either remove the filtering or add to _GRANDFATHERED with justification."
        )
