"""WP03 coordination-branch tests for ``agent mission create``.

Issue #1348 — these tests exercise the topology foundation: every mission
must mint a deterministic per-mission coordination branch
``kitty/mission-<slug>-<mid8>`` parented off the target branch, persist the
ref in ``meta.json``, expose it in the ``--json`` output, and refuse a
divergent re-create unless the operator explicitly opts in.

The pure-helper tests (``ensure_coordination_branch``) cover idempotency,
divergence detection, and force-recreate semantics without booting the CLI.
The integration tests cover the end-to-end behaviour through
``create_mission_core`` and the typer CLI surface.
"""

from __future__ import annotations

import json
import subprocess
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.core.mission_creation import MissionCreationResult

from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.core.mission_creation import create_mission_core
from specify_cli.missions._create import (
    CoordinationBranchDiverged,
    coordination_branch_name,
    ensure_coordination_branch,
)


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"


# ---------------------------------------------------------------------------
# Repo + mission helpers
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "-m", "init", "--allow-empty")


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").title()
    return {
        "friendly_name": title,
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _patch_repo_environment(repo: Path) -> list[AbstractContextManager[Any]]:
    """Common patch stack for ``create_mission_core`` against ``repo``."""
    return [
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ]


def _create(repo: Path, slug: str, **kwargs: Any) -> MissionCreationResult:
    patches = _patch_repo_environment(repo)
    for p in patches:
        p.__enter__()
    try:
        return create_mission_core(repo, slug, **_mission_summary(slug), **kwargs)
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)


def _branch_exists(repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _branch_sha(repo: Path, branch: str) -> str:
    return _git(repo, "rev-parse", branch).stdout.strip()


# ---------------------------------------------------------------------------
# Pure-helper tests (no CLI, no mission scaffold)
# ---------------------------------------------------------------------------


def test_coordination_branch_name_uses_mid8(tmp_path: Path) -> None:
    """The branch name must include the 8-char ULID prefix as the disambiguator (FR-015)."""
    mission_id = "01KSPTVWZ9ABCDEFGHJKMNPQRS"
    name = coordination_branch_name("my-feature-01KSPTVW", mission_id)
    assert name == "kitty/mission-my-feature-01KSPTVW"
    assert "01KSPTVW" in name
    assert name.startswith("kitty/mission-")


def test_ensure_creates_branch_when_missing(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    main_sha = _branch_sha(tmp_path, "main")

    outcome = ensure_coordination_branch(
        repo_root=tmp_path,
        mission_slug="my-feature-01KSPTVW",
        mission_id="01KSPTVWZ9ABCDEFGHJKMNPQRS",
        target_branch="main",
    )
    assert outcome.created is True
    assert outcome.force_recreated is False
    assert _branch_exists(tmp_path, outcome.branch_name)
    assert _branch_sha(tmp_path, outcome.branch_name) == main_sha


def test_ensure_is_idempotent_when_branch_at_target(tmp_path: Path) -> None:
    """Re-running against an existing branch that is at the target is a silent no-op."""
    _init_repo(tmp_path)
    args = dict(
        repo_root=tmp_path,
        mission_slug="my-feature-01KSPTVW",
        mission_id="01KSPTVWZ9ABCDEFGHJKMNPQRS",
        target_branch="main",
    )

    first = ensure_coordination_branch(**args)
    sha_after_first = _branch_sha(tmp_path, first.branch_name)

    second = ensure_coordination_branch(**args)
    assert second.created is False
    assert second.force_recreated is False
    assert second.branch_name == first.branch_name
    assert _branch_sha(tmp_path, second.branch_name) == sha_after_first


def test_ensure_raises_when_branch_diverged(tmp_path: Path) -> None:
    """A branch advanced past the target raises CoordinationBranchDiverged with structured fields."""
    _init_repo(tmp_path)
    args = dict(
        repo_root=tmp_path,
        mission_slug="my-feature-01KSPTVW",
        mission_id="01KSPTVWZ9ABCDEFGHJKMNPQRS",
        target_branch="main",
    )
    first = ensure_coordination_branch(**args)
    branch = first.branch_name

    # Advance the coordination branch off the target so it diverges.
    _git(tmp_path, "checkout", branch)
    (tmp_path / "drift.txt").write_text("drifted", encoding="utf-8")
    _git(tmp_path, "add", "drift.txt")
    _git(tmp_path, "commit", "-m", "drift")
    _git(tmp_path, "checkout", "main")

    with pytest.raises(CoordinationBranchDiverged) as exc_info:
        ensure_coordination_branch(**args)

    err = exc_info.value
    assert err.error_code == "COORDINATION_BRANCH_DIVERGED"
    assert err.coordination_branch == branch
    assert err.target_branch == "main"
    payload = err.to_dict()
    assert payload["error_code"] == "COORDINATION_BRANCH_DIVERGED"
    assert payload["coordination_branch"] == branch
    assert payload["target_branch"] == "main"
    assert "next_step" in payload and payload["next_step"]


def test_force_recreate_resets_diverged_branch_to_target(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    args = dict(
        repo_root=tmp_path,
        mission_slug="my-feature-01KSPTVW",
        mission_id="01KSPTVWZ9ABCDEFGHJKMNPQRS",
        target_branch="main",
    )
    first = ensure_coordination_branch(**args)
    branch = first.branch_name

    _git(tmp_path, "checkout", branch)
    (tmp_path / "drift.txt").write_text("drifted", encoding="utf-8")
    _git(tmp_path, "add", "drift.txt")
    _git(tmp_path, "commit", "-m", "drift")
    _git(tmp_path, "checkout", "main")

    main_sha = _branch_sha(tmp_path, "main")
    outcome = ensure_coordination_branch(**args, force_recreate=True)
    assert outcome.created is True
    assert outcome.force_recreated is True
    # Reset to target sha — the drift commit is gone from the branch tip.
    assert _branch_sha(tmp_path, outcome.branch_name) == main_sha


# ---------------------------------------------------------------------------
# Integration tests (via create_mission_core)
# ---------------------------------------------------------------------------


def test_mission_create_mints_coordination_branch(tmp_path: Path) -> None:
    """A fresh mission_create call leaves the coordination branch on disk."""
    _init_repo(tmp_path)
    result = _create(tmp_path, "auth-flow")

    assert result.coordination_branch is not None
    assert result.coordination_branch_created is True
    assert result.coordination_branch.startswith("kitty/mission-auth-flow-")
    assert _branch_exists(tmp_path, result.coordination_branch)


def test_mission_create_idempotent_second_run(tmp_path: Path) -> None:
    """Re-creating the same mission slug (slug collision permitted in same dir) is a no-op for the branch.

    Because each ``mission create`` mints a fresh ULID, two calls with the
    same input slug yield *different* mission directories and therefore
    different coordination branch names. The idempotency guarantee at the
    branch level is exercised by directly invoking
    ``ensure_coordination_branch`` twice for the same identity (already
    covered above), and at the mission level we assert that re-running with
    the *same* identity (same mission_id) does not raise.
    """
    _init_repo(tmp_path)
    result = _create(tmp_path, "twice-run")
    mission_id = result.meta["mission_id"]

    # Direct second invocation with the same identity: no error, no churn.
    second = ensure_coordination_branch(
        repo_root=tmp_path,
        mission_slug=result.mission_slug,
        mission_id=mission_id,
        target_branch="main",
    )
    assert second.created is False
    assert second.branch_name == result.coordination_branch


def test_meta_json_contains_coordination_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    result = _create(tmp_path, "persist-meta")

    meta_path = result.feature_dir / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert meta["coordination_branch"] == result.coordination_branch
    assert meta["coordination_branch"].startswith("kitty/mission-persist-meta-")


def test_create_json_output_contains_coordination_branch(tmp_path: Path) -> None:
    """The CLI ``--json`` payload exposes ``coordination_branch`` at the top level."""
    _init_repo(tmp_path)

    # Patch the CLI's view of project root + branch context so we drive the
    # actual typer entry point through a tmp repo.
    runner = CliRunner()
    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.mission.get_current_branch", return_value="main"),
    ):
        result = runner.invoke(
            mission_app,
            [
                "create",
                "cli-json-test",
                "--json",
                "--target-branch",
                "main",
                "--friendly-name",
                "CLI JSON Test",
                "--purpose-tldr",
                "Validate JSON output includes coordination_branch.",
                "--purpose-context",
                "Issue #1348 — downstream tooling needs the canonical ref in the CLI JSON.",
            ],
        )

    assert result.exit_code == 0, result.output
    # Some lines in stdout may be informational; find the JSON payload.
    payload = None
    for line in result.output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    assert payload is not None, f"No JSON payload in CLI output: {result.output!r}"
    assert payload.get("result") == "success"
    assert "coordination_branch" in payload
    assert payload["coordination_branch"].startswith("kitty/mission-cli-json-test-")
    assert payload["coordination_branch_created"] is True
