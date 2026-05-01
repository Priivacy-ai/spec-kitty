"""T023 — Windows-native messaging tests for ``spec-kitty migrate``.

Covers the happy-path (moved) and conflict-path (quarantined) output shapes
contracted in ``contracts/cli-migrate.md``.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest``
CI job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Both tests monkeypatch LOCALAPPDATA, USERPROFILE, and HOME to point into a
temporary directory, then invoke the migrate command via the Typer
CliRunner and assert the contracted message shapes are present and that
no legacy path literals appear in the output.

Spec IDs: FR-006, FR-012, FR-013, NFR-005
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.mark.windows_ci
def test_migrate_windows_moved_output(tmp_path, monkeypatch):
    """Happy-path: legacy tree moved — output contains the migration banner."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "User"))
    monkeypatch.setenv("HOME", str(tmp_path / "User"))

    # Create a legacy ~/.spec-kitty tree with content
    legacy = tmp_path / "User" / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "data.txt").write_text("legacy content")

    from specify_cli import app  # root typer app

    runner = CliRunner()
    result = runner.invoke(app, ["migrate", "--force"])

    output = result.stdout or ""

    # Contract: migration summary banner must appear
    assert "Migrated Spec Kitty runtime state" in output, f"Expected migration banner not found in output:\n{output}"
    # Contract: canonical location line must appear
    assert "Canonical location:" in output, f"Expected 'Canonical location:' not found in output:\n{output}"
    # Contract: AppData path (Windows-native) or spec-kitty directory name must appear
    assert "AppData" in output or "spec-kitty" in output.lower(), f"Expected Windows-native path or 'spec-kitty' not found in output:\n{output}"
    # Contract: no legacy literal path forms
    assert "~/.kittify" not in output, f"Legacy path '~/.kittify' found in migrate output:\n{output}"
    assert "~/.spec-kitty" not in output, f"Legacy path '~/.spec-kitty' found in migrate output:\n{output}"


@pytest.mark.windows_ci
def test_migrate_windows_quarantined_output(tmp_path, monkeypatch):
    """Conflict-path: destination non-empty — output contains quarantine message."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "User"))
    monkeypatch.setenv("HOME", str(tmp_path / "User"))

    # Create legacy tree
    legacy = tmp_path / "User" / ".spec-kitty"
    legacy.mkdir(parents=True)
    (legacy / "data.txt").write_text("legacy content")

    # Create non-empty destination so quarantine path is triggered
    dest = tmp_path / "LocalAppData" / "spec-kitty"
    dest.mkdir(parents=True)
    (dest / "existing.txt").write_text("existing canonical state")

    from specify_cli import app  # root typer app

    runner = CliRunner()
    result = runner.invoke(app, ["migrate", "--force"])

    output = result.stdout or ""

    # Contract: quarantine message variants
    assert "Destination already contained state" in output or "preserved as backups" in output, f"Expected quarantine message not found in output:\n{output}"
    # Contract: backup suffix must appear
    assert ".bak-" in output, f"Expected '.bak-' timestamp suffix not found in output:\n{output}"
    # Contract: no legacy literal path forms
    assert "~/.kittify" not in output, f"Legacy path '~/.kittify' found in migrate output:\n{output}"
    assert "~/.spec-kitty" not in output, f"Legacy path '~/.spec-kitty' found in migrate output:\n{output}"
