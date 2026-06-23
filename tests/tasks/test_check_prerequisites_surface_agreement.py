"""Regression (#2087): check-prerequisites resolves the PRIMARY planning surface,
agreeing with finalize-tasks (which anchors to the primary checkout).

Genuine red-first capture through the STABLE entry point (the
``check-prerequisites`` command), not a test of the fix's new helper. On the
pre-fix code ``check_prerequisites`` resolved ``feature_dir`` via the coord-aware
``_find_feature_directory`` → the coordination worktree, while ``finalize-tasks``
reads its inputs from the PRIMARY checkout. The command test below patches the
coord-aware resolver to return a coordination-worktree path and asserts the
command STILL reports the primary dir — it returns the coord path (and the
assertion FAILS) on the pre-fix code, and the primary path (assertion passes)
once ``check_prerequisites`` delegates to the primary anchor finalize uses.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from specify_cli.cli.commands.agent.mission import app
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()

# Production-shaped mission slug (human-slug + mid8).
_SLUG = "single-authority-topology-cleanup-01KVRJ6P"
_MISSION_ID = "01KVRJ6PC66DWS32M30YVPAE28"


def _git_init(repo: Path) -> None:
    def _git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

    _git("init", "-q", "-b", "feat/x")
    _git("config", "user.email", "t@example.invalid")
    _git("config", "user.name", "Test")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md")
    _git("commit", "-q", "-m", "init")


def _write_mission_dir(base: Path, *, coordination: bool) -> Path:
    feature_dir = base / "kitty-specs" / _SLUG
    (feature_dir / "tasks").mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _SLUG,
        "slug": _SLUG,
        "target_branch": "feat/x",
    }
    if coordination:
        meta["coordination_branch"] = f"kitty/mission-{_SLUG}"
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "spec.md").write_text(
        "# Spec\n## Functional Requirements\n"
        "| ID | Requirement | Acceptance | Status |\n| - | - | - | - |\n"
        "| FR-001 | x | y | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text("## WP01\n**Requirement Refs**: FR-001\n", encoding="utf-8")
    return feature_dir


def _json_payload(stdout: str) -> dict[str, object]:
    lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    assert lines, stdout
    return json.loads(lines[-1])


def test_check_prerequisites_reports_primary_not_coord(tmp_path: Path) -> None:
    """The command reports the PRIMARY dir even when the coord-aware resolver
    would return a coordination worktree — capturing the #2087 surface split."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    primary = _write_mission_dir(repo, coordination=True)
    # The coordination worktree the coord-aware resolver would pick.
    coord_dir = _write_mission_dir(repo / ".worktrees" / f"{_SLUG}-coord", coordination=True)
    assert ".worktrees" in str(coord_dir)

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=repo),
        patch("specify_cli.cli.commands.agent.mission._enforce_git_preflight"),
        # The coord-aware resolver returns the coordination worktree. Pre-fix the
        # command used THIS as feature_dir; post-fix it must prefer the primary anchor.
        patch(
            "specify_cli.cli.commands.agent.mission._find_feature_directory",
            return_value=coord_dir,
        ),
    ):
        result = runner.invoke(
            app,
            ["check-prerequisites", "--mission", _SLUG, "--json", "--paths-only", "--include-tasks"],
        )

    payload = _json_payload(result.stdout)
    feature_dir = str(payload.get("feature_dir", ""))
    assert ".worktrees" not in feature_dir, f"reported the coord worktree: {feature_dir}"
    assert feature_dir == str(primary)


# --- pure helper contract tests (supporting the command behaviour above) ------


def test_primary_anchored_dir_agrees_with_finalize_anchor(tmp_path: Path) -> None:
    # Lazy import: the new helper does not exist on pre-fix code; keeping this out
    # of module scope lets the command-level capture above still collect+run RED.
    from specify_cli.cli.commands.agent.mission import _primary_anchored_feature_dir

    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    primary = _write_mission_dir(repo, coordination=True)
    resolved = _primary_anchored_feature_dir(repo, _SLUG)
    assert resolved == primary == primary_feature_dir_for_mission(repo, _SLUG)


def test_primary_anchored_dir_none_when_absent_or_empty(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.mission import _primary_anchored_feature_dir

    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    assert _primary_anchored_feature_dir(repo, "no-such-mission-01XXXXXXXX") is None
    assert _primary_anchored_feature_dir(tmp_path, None) is None
    assert _primary_anchored_feature_dir(tmp_path, "   ") is None
