"""Tests for the ``spec-kitty team-projection publish`` CLI command (§3.5, §5).

Exercises the command surface end-to-end (git repo + real mission) rather
than re-testing ``write_team_projection`` internals (already covered by
``test_write.py``).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.utils import write_wp

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def test_publish_command_writes_artifacts(
    temp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.cli.commands.team_projection import app

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(temp_repo))

    result = runner.invoke(app, ["publish"])

    assert result.exit_code == 0, result.output
    derived = temp_repo / ".kittify" / "derived"
    assert (derived / "team-index.json").exists()
    assert (derived / slug / "team-snapshot.json").exists()
    assert (derived / "attestation-manifest.json").exists()


def test_publish_command_json_output(
    temp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.cli.commands.team_projection import app

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(temp_repo))

    result = runner.invoke(app, ["publish", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "attestation_manifest/v1"


def test_publish_command_dirty_tree_nonzero_exit(
    temp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.cli.commands.team_projection import app

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    (temp_repo / "kitty-specs" / "untracked.txt").write_text("x", encoding="utf-8")

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(temp_repo))

    result = runner.invoke(app, ["publish"])

    assert result.exit_code != 0
