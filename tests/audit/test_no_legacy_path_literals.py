"""T024 — Static + behavioral audit: no legacy Windows-unsafe path literals
reach user-facing output.

Two complementary checks:

1. **Static grep over CLI command tree**: any ``~/.kittify`` / ``~/.spec-kitty``
   literal in ``src/specify_cli/cli/`` (non-comment lines) is flagged.  The
   CLI command tree is where user-facing ``console.print`` / ``typer.echo``
   lives, so a static check is sufficient there.

2. **Behavioral test of resolver nudges**: the ``_emit_migrate_nudge`` helpers
   in ``src/specify_cli/runtime/resolver.py`` and ``src/doctrine/resolver.py``
   print a one-time stderr message.  DRIFT-6 from the mission review showed
   the nudge was hardcoded to ``~/.kittify/`` regardless of platform.  These
   behavioral tests invoke the helpers under a mocked ``SPEC_KITTY_HOME`` that
   masquerades as the unified Windows root and assert the output contains the
   mocked real path (no tilde literal).

Internal modules (``runtime/bootstrap.py``, ``sync/queue.py``, ``state_contract.py``,
migration scripts, etc.) reference ``~/.kittify`` / ``~/.spec-kitty`` freely in
docstrings, inline comments, and string-literal ``path_pattern`` metadata.
None of that is user-facing runtime output.  A textual tree-wide grep produces
too many false positives, so the audit is scoped to the files that actually
emit to users.

No ``windows_ci`` marker — these checks run on every platform.

Spec IDs: FR-013, SC-002 (second-pass remediation)
"""

from __future__ import annotations

import importlib
import io
import os
import pathlib
import re
import sys
from contextlib import redirect_stderr

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


def _capture_nudge(module_name: str, runtime_home: pathlib.Path) -> str:
    """Import the named module, reset its nudge flag, and capture stderr on call.

    Uses ``SPEC_KITTY_HOME`` to pin the runtime home to a tmp path so the
    rendered message is deterministic and does not depend on the real user's
    home directory.  Returns whatever the nudge printed to stderr.
    """
    old_env = os.environ.get("SPEC_KITTY_HOME")
    os.environ["SPEC_KITTY_HOME"] = str(runtime_home)
    try:
        # Fresh import so module-level state is clean
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        module = importlib.import_module(module_name)
        module._reset_migrate_nudge()
        buf = io.StringIO()
        with redirect_stderr(buf):
            module._emit_migrate_nudge()
        return buf.getvalue()
    finally:
        if old_env is None:
            os.environ.pop("SPEC_KITTY_HOME", None)
        else:
            os.environ["SPEC_KITTY_HOME"] = old_env


def test_runtime_resolver_nudge_renders_real_runtime_path(tmp_path: pathlib.Path) -> None:
    """Assert specify_cli.runtime.resolver nudge prints the actual runtime path.

    DRIFT-6 remediation: the nudge must render via ``render_runtime_path`` so
    Windows users see the real ``%LOCALAPPDATA%\\spec-kitty\\`` path, not a
    hard-coded ``~/.kittify/`` literal.  We pin ``SPEC_KITTY_HOME`` to a tmp
    path and assert the captured stderr contains that path verbatim (or its
    tilde-compressed form on POSIX when under $HOME — tmp_path here is outside
    $HOME so we get the absolute form).
    """
    fake_home = tmp_path / "runtime-home"
    output = _capture_nudge("specify_cli.runtime.resolver", fake_home)
    assert str(fake_home) in output, (
        f"Resolver nudge did not render the real runtime path.\n"
        f"Expected substring: {fake_home}\n"
        f"Got: {output!r}"
    )
    assert "~/.kittify/" not in output, (
        f"Resolver nudge still contains a legacy tilde literal:\n{output!r}"
    )


def test_doctrine_resolver_nudge_renders_real_runtime_path(tmp_path: pathlib.Path) -> None:
    """Mirror assertion for the doctrine package's resolver nudge."""
    fake_home = tmp_path / "doctrine-runtime-home"
    output = _capture_nudge("doctrine.resolver", fake_home)
    assert str(fake_home) in output, (
        f"Doctrine resolver nudge did not render the real runtime path.\n"
        f"Expected substring: {fake_home}\n"
        f"Got: {output!r}"
    )
    assert "~/.kittify/" not in output, (
        f"Doctrine resolver nudge still contains a legacy tilde literal:\n{output!r}"
    )
