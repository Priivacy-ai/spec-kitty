"""Regression: read-surface == write-surface for a coordination mission's
healthy verbatim commit path (PR #2662 adversarial-squad finding).

The implement-claim idempotency guard skips files already identical on the ref
they will be COMMITTED to, so a re-discovered edit does not produce an empty
commit that ``safe_commit`` rejects. On the healthy ``placement_ref is not
None`` path the whole batch commits VERBATIM to ``placement_ref.ref`` (the
coord ref on a coordination mission -- the C-004/#2160 deferral leaves it
un-partitioned). Before the fix the guard compared a PRIMARY artifact against
``HEAD`` while the write went to coord, so a PRIMARY ``spec.md`` already on
coord but differing from ``HEAD`` was re-committed → empty commit → the SECOND
claim hard-failed with ``typer.Exit(1)``.

These tests use the REAL ``BookkeepingTransaction`` (the sibling write-side
suite monkeypatches a fake, which is why the empty-commit was never exercised).
The invariant: the read ref must be the SAME surface as the write target.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer

from mission_runtime.context import CommitTarget

# Real-git-repo + real BookkeepingTransaction integration test (mirrors the
# sibling test_tasks_move_task_cwd.py markers so a CI gate selects it and the
# marker-convention / orphan-surface arch gates stay green).
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_PLANNING_BRANCH = "mission/coord-idempotency-demo"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _seed_coord_mission_real(tmp_path: Path) -> tuple[Path, Path, str, str, CommitTarget]:
    """A real git repo with a coordination mission, an empty coord branch, and a
    genuinely-dirty PRIMARY ``spec.md`` (revised in the working tree, differs
    from the committed HEAD baseline). Returns (repo, feature_dir, mission_slug,
    spec_rel, coord_target)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", _PLANNING_BRANCH)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")

    mission_slug = "coord-idempotency-demo"
    mission_id = "01J9COORDIDEMPOTENCYXXXXXX"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{mission_slug}-{mid8}"
    _git(repo, "branch", coord_branch)

    feature_dir = repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": mission_slug,
                "mid8": mid8,
                "mission_type": "software-dev",
                "target_branch": _PLANNING_BRANCH,
                "coordination_branch": coord_branch,
                "topology": "coord",
                "created_at": "2026-07-14T00:00:00+00:00",
                "friendly_name": "coord idempotency demo",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    spec = feature_dir / "spec.md"
    spec.write_text("# Spec\noriginal\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed feature dir (spec=original on HEAD)")
    # Genuinely-dirty PRIMARY artifact: differs from the HEAD baseline.
    spec.write_text("# Spec\nrevised\n", encoding="utf-8")

    return repo, feature_dir, mission_slug, f"kitty-specs/{mission_slug}/spec.md", CommitTarget(ref=coord_branch)


def _claim(repo: Path, feature_dir: Path, mission_slug: str, wp_id: str, target: CommitTarget) -> None:
    from specify_cli.cli.commands.implement import _ensure_planning_artifacts_committed_git

    _ensure_planning_artifacts_committed_git(
        repo_root=repo,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=wp_id,
        planning_branch=_PLANNING_BRANCH,
        auto_commit=True,
        placement_ref=target,
    )


class TestCoordHealthyPathIdempotency:
    def test_repeated_claim_of_a_coord_identical_primary_artifact_does_not_hard_fail(
        self, tmp_path: Path
    ) -> None:
        """The read surface follows the verbatim write target: a PRIMARY artifact
        already committed to the coord ref is dropped on the next claim instead of
        producing an empty commit that ``Exit(1)``s. Pre-fix this raised on claim 2.
        """
        repo, feature_dir, mission_slug, spec_rel, target = _seed_coord_mission_real(tmp_path)

        # Claim 1: spec.md is dirty vs HEAD and absent on coord -> committed to coord.
        _claim(repo, feature_dir, mission_slug, "WP01", target)
        assert _git(repo, "show", f"{target.ref}:{spec_rel}") == "# Spec\nrevised"

        # Claim 2: spec.md is STILL dirty vs HEAD but now identical on the coord
        # WRITE surface -> must be dropped by the idempotency guard, no empty
        # commit, no raise. (Pre-fix: compared vs HEAD -> re-committed -> Exit(1).)
        try:
            _claim(repo, feature_dir, mission_slug, "WP02", target)
        except typer.Exit as exc:  # pragma: no cover - the bug this test guards
            pytest.fail(
                f"claim 2 hard-failed with typer.Exit({exc.exit_code}) — the read "
                "surface (HEAD) diverged from the write surface (coord ref); the "
                "idempotency guard must compare against the write target"
            )
        # coord unchanged (the identical artifact was dropped, not re-committed).
        assert _git(repo, "show", f"{target.ref}:{spec_rel}") == "# Spec\nrevised"
