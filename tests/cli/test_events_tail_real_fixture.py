"""Real-fixture end-to-end test for `spec-kitty events tail` (WP04, T030).

Companion to ``tests/cli/test_events_tail.py`` (see that file's docstring for
the full picture). This is a SEPARATE FILE, not a function-level marker
override, specifically so this one test's module-level ``pytestmark`` can
carry ONLY ``integration``/``git_repo`` -- no ``fast`` -- while the rest of
the CLI-shell suite stays ``fast``. pytest marks stack (a function inheriting
a module-level ``fast`` mark from its module cannot un-mark itself with a
function-level decorator alone), so the clean split is a dedicated module,
mirroring the established pattern elsewhere in this repo, e.g.
``tests/cli/commands/test_agent_mission_commit_to_branch.py`` (module-level
``pytestmark = pytest.mark.git_repo``, no ``fast``).

Marker/CI discipline (C-008/SK-144): collected by ``integration-tests-cli``,
which selects ``tests/cli/ tests/specify_cli/cli/ -m 'not windows_ci and
(git_repo or integration)'`` (``.github/workflows/ci-quality.yml``) -- and
explicitly NOT by ``fast-tests-cli`` (``-m "fast and not windows_ci"``),
since this module carries no ``fast`` marker.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands import events as events_cli

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

# Mirrors test_events_tail.py's exact mounting pattern -- see that file's
# docstring for why a throwaway root Typer app is required.
_root_app = typer.Typer()
_root_app.add_typer(events_cli.app, name="events")


def _write_events(feature_dir: Path, events: list[dict]) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    log_path = feature_dir / "status.events.jsonl"
    with log_path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")
    return log_path


def test_events_tail_real_fixture_end_to_end(tmp_path: Path) -> None:
    """T030 (real-fixture tier): exercises the real core end-to-end against a
    real git repository with a real kitty-specs/<slug>/meta.json and a real
    status.events.jsonl -- NOT an all-mocked core, and resolve_mission_handle
    is never mocked either. Collected by integration-tests-cli.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)  # noqa: S607
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)  # noqa: S607
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)  # noqa: S607

    mission_slug = "001-real-fixture-mission"
    mission_id = "01REALFIXTUREMISSION00000"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": mission_slug, "mission_id": mission_id}),
        encoding="utf-8",
    )
    _write_events(feature_dir, [{"event_id": "real-1"}, {"event_id": "real-2"}])
    (repo_root / ".kittify").mkdir()

    result = runner.invoke(
        _root_app,
        ["events", "tail", "--mission", mission_slug, "--json", "--once"],
        env={"SPECIFY_REPO_ROOT": str(repo_root)},
    )

    assert result.exit_code == 0, result.output
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    parsed = [json.loads(line) for line in lines]
    assert [p["event_id"] for p in parsed] == ["real-1", "real-2"]
