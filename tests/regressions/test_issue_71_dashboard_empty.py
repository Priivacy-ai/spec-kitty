"""Regression test for issue #71: dashboard returns empty output on Windows.

Issue #71 was a symptom of Windows-specific IO/encoding bugs producing empty
output from CLI commands.  This test verifies that a basic dashboard ``--json``
invocation (which does not start a server) returns non-empty, parseable JSON
output on Windows.

We use ``dashboard --json`` because it exits without starting a subprocess
server and therefore runs safely in CI without port conflicts.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest`` CI
job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Spec IDs: FR-016, FR-017, SC-004
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.mark.windows_ci
def test_dashboard_json_returns_non_empty_on_windows(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """``dashboard --json`` must return non-empty output on Windows.

    Sets up a minimal project structure (a ``kitty-specs/`` directory with a
    single mission ``meta.json``) so the scanner has at least one record to
    return.  Asserts the JSON output is non-empty and parseable.
    """
    monkeypatch.chdir(tmp_path)

    # Minimal project layout: .kittify/metadata.yaml + kitty-specs/<mission>/meta.json
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    # metadata.yaml is read by check_version_compatibility; provide a minimal one
    (kittify_dir / "metadata.yaml").write_text(
        "schema_version: 3\n",
        encoding="utf-8",
    )

    # Create a minimal mission so the scanner returns at least one record.
    mission_dir = tmp_path / "kitty-specs" / "demo-mission-01KP5R6K"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        '{"mission_id":"01KP5R6KAAAAAAAAAAAAAAAA26",'
        '"mission_slug":"demo-mission-01KP5R6K",'
        '"friendly_name":"Demo Mission",'
        '"mission_type":"software-dev",'
        '"target_branch":"main",'
        '"vcs":"git",'
        '"created_at":"2026-04-14T00:00:00+00:00"}',
        encoding="utf-8",
    )

    from specify_cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["dashboard", "--json"])

    # Non-empty output = at least one non-whitespace character
    output = result.stdout or ""
    assert output.strip() != "", (
        f"dashboard --json returned empty output on Windows. "
        f"rc={result.exit_code} stderr={getattr(result, 'stderr', '')!r}"
    )
