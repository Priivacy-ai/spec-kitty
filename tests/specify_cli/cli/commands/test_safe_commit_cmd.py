"""Tests for the public ``spec-kitty safe-commit`` command."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()


def _init_spec_kitty_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".kittify/config.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)


@pytest.mark.parametrize(
    "message",
    [
        "chore: apply spec-kitty upgrade changes (3.0.3 -> 3.1.4)",
        "chore: release 3.2.0",
        "release: 3.2.0",
        "chore(099-demo): record done transitions for merged WPs",
    ],
)
def test_public_safe_commit_does_not_honor_internal_protected_branch_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    """Public CLI messages must not spoof internal safe_commit exceptions."""
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)
    _init_spec_kitty_repo(tmp_path)
    (tmp_path / "change.txt").write_text("protected branch change\n", encoding="utf-8")
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Post-#1348 (WP02): --to-branch is required. The test runs on
        # `main` (the protected branch) so the helper rejects the commit at the
        # protected-branch check, which is what this test asserts.
        result = runner.invoke(
            cli_app,
            ["safe-commit", "--to-branch", "main", "--message", message, "--json", "change.txt"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    payload = json.loads(result.stdout)
    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert result.exit_code == 1
    assert payload["success"] is False
    assert "protected branch 'main'" in payload["error"]
    assert head_after == head_before


def test_public_safe_commit_rejects_protected_branch_in_test_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC_KITTY_TEST_MODE must not let public safe-commit write to main."""
    monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)
    _init_spec_kitty_repo(tmp_path)
    (tmp_path / "change.txt").write_text("protected branch change\n", encoding="utf-8")
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            [
                "safe-commit",
                "--to-branch",
                "main",
                "--message",
                "WP01: arbitrary status write",
                "--json",
                "change.txt",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    payload = json.loads(result.stdout)
    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert result.exit_code == 1
    assert payload["success"] is False
    assert "protected branch 'main'" in payload["error"]
    assert head_after == head_before


@pytest.mark.regression
def test_public_safe_commit_succeeds_after_merged_branch_deleted_3033(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3033: post-merge write fails once the merged mission branch is pruned.

    ``spec-kitty safe-commit`` (no ``--to-branch``, which is load-bearing --
    passing it short-circuits the defect at
    ``src/specify_cli/cli/commands/safe_commit_cmd.py:267``) resolves a
    PRIMARY-kind mission artifact's destination through
    ``_resolve_mission_aware_target`` ->
    ``mission_runtime.resolve_placement_only`` ->
    ``specify_cli.core.paths.get_feature_target_branch``
    (``src/specify_cli/core/paths.py:696-733``): a bare ``meta.json`` read of
    ``target_branch`` with NO existence check against git and no
    lifecycle-phase input. Once the mission's feature branch has been merged
    and pruned (``git branch -D``) -- exactly what happens after
    ``spec-kitty merge`` -- and a later pass (e.g. authoring the
    retrospective) works from a *different* checked-out branch, the resolved
    ``CommitTarget.ref`` still points at the now-nonexistent feature branch.
    ``safe_commit``'s embedded HEAD-match guard then refuses the commit with
    ``safe_commit: worktree ... HEAD is 'review/...', expected 'feat/...'``.

    ``retrospective.yaml`` is deliberately the changeset here because
    ``mission-review-report.md`` is NOT a member of
    ``_MISSION_FILE_KIND_BY_BASENAME``
    (``src/mission_runtime/artifacts.py:195-220``) -- a commit for that
    basename falls through the mission-aware branch entirely and lands on the
    generic HEAD path, where it would *succeed* despite the same pruned
    branch, masking this defect. Also: ``spec-kitty review`` itself performs
    no commit, so this defect is NOT reachable through the review command
    despite what issue #3033's body says -- it is reachable through any
    direct ``safe-commit`` of a PRIMARY-kind mission artifact (retrospective,
    spec, plan, tasks, analysis-report, ...) once the feature branch is gone.

    This test asserts the OUTCOME (``success`` / ``committed``), not a
    particular destination branch: a fix that special-cases "commit to HEAD"
    would relieve this symptom while leaving the same hole open for the
    retrospective terminus and the acceptance-matrix refresh, both of which
    share the same ``get_feature_target_branch`` read.
    """
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)

    mission_slug = "relational-cutover-01KYHHR8"
    feature_branch = f"feat/{mission_slug}"
    postmerge_branch = f"review/{mission_slug}-postmerge"

    _init_spec_kitty_repo(tmp_path)

    def _git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    _git("checkout", "-q", "-b", feature_branch)
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    meta = {
        "mission_id": "01KYHHR8RELATIONALCUT0001",
        "mission_slug": mission_slug,
        "mission_type": "software-dev",
        "target_branch": feature_branch,
        "friendly_name": "Relational cutover",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"chore({mission_slug}): seed mission meta"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Merge into main and prune the merged branch -- exactly what
    # `spec-kitty merge` + branch cleanup leaves behind.
    _git("checkout", "-q", "main")
    _git("merge", "-q", "--no-ff", feature_branch, "-m", f"Merge {feature_branch}")
    _git("branch", "-D", feature_branch)

    # A later retrospective pass works from a fresh branch -- the merged
    # mission branch no longer exists anywhere in this repo.
    _git("checkout", "-q", "-b", postmerge_branch)

    retro_path = feature_dir / "retrospective.yaml"
    retro_path.write_text(
        "summary: Relational cutover retrospective\n"
        "lessons_learned:\n"
        "  - Post-merge writes must not require the merged branch to still exist.\n",
        encoding="utf-8",
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            [
                "safe-commit",
                "--message",
                f"chore({mission_slug}): record retrospective",
                "--json",
                str(retro_path.relative_to(tmp_path)),
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    payload = json.loads(result.stdout)

    assert payload["success"] is True, payload
    assert payload["committed"] is True, payload
