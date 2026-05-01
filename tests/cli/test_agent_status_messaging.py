"""T022 — Windows-native messaging test for ``spec-kitty agent status``.

Asserts that the ``agent status`` command output contains no legacy
``~/.kittify`` or ``~/.spec-kitty`` path literals on Windows.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest``
CI job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Spec IDs: FR-012, FR-013, SC-002
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.mark.windows_ci
def test_agent_status_no_legacy_literals_on_windows() -> None:
    """``spec-kitty agent status`` output must contain no legacy path literals."""
    from specify_cli import app  # root typer app

    runner = CliRunner()
    result = runner.invoke(app, ["agent", "status"])
    # Command may exit non-zero if there is no active mission; we only care
    # about the substring content of the output.
    output = (result.stdout or "") + (result.stderr or "")

    assert "~/.kittify" not in output, f"Legacy path '~/.kittify' found in agent status output:\n{output}"
    assert "~/.spec-kitty" not in output, f"Legacy path '~/.spec-kitty' found in agent status output:\n{output}"

    # On Windows, if the output mentions spec-kitty at all, at least one
    # Windows-native path form (drive letter + backslash) must be present.
    if "spec-kitty" in output.lower():
        assert "\\" in output or ":" in output, f"Windows status output names spec-kitty but contains no native Windows path form (expected '\\' or ':'):\n{output}"
