"""T024 — Static audit: no legacy Windows-unsafe path literals in CLI command tree.

Blocks any future PR that reintroduces ``~/.kittify`` or ``~/.spec-kitty``
string literals in user-facing code under ``src/specify_cli/cli/``.

Pure-comment lines (lines whose first non-whitespace character is ``#``) are
excluded because comments are not user-facing output.  Any other line that
contains ``~/.(kittify|spec-kitty)`` is flagged as a violation.

No ``windows_ci`` marker — this is a static check that runs on every platform.

Spec IDs: FR-013, SC-002
"""

from __future__ import annotations

import pathlib
import re


# Match the bare tilde-path anywhere on a line.
LITERAL = re.compile(r'~/\.(kittify|spec-kitty)')
# Comment detector: line starts with optional whitespace then '#'.
COMMENT = re.compile(r'^\s*#')


def test_no_legacy_path_literals_in_cli_commands() -> None:
    """Assert zero ~/.(kittify|spec-kitty) literals in CLI command tree (non-comment lines)."""
    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "cli"
    violations: list[str] = []
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if COMMENT.match(line):
                continue  # skip pure comments; they are not user-facing output
            if LITERAL.search(line):
                violations.append(
                    f"{py.relative_to(root.parents[2])}:{i}: {line.strip()}"
                )
    assert not violations, (
        "Legacy Windows-unsafe path literals reintroduced in CLI command tree:\n  "
        + "\n  ".join(violations)
    )
