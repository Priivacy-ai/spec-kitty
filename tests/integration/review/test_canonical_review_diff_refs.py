from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.workflow import _resolve_review_context
from specify_cli.frontmatter import write_frontmatter
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json

pytestmark = pytest.mark.git_repo


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_review_diff_refs_use_canonical_manifest_for_mission_prefixed_slug(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    mission_slug = "mission-canonical-refs"
    mission_branch = "kitty/mission-canonical-refs"
    lane_branch = "kitty/mission-canonical-refs-lane-a"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_frontmatter(
        tasks_dir / "WP03-review-prompt-isolation.md",
        {
            "work_package_id": "WP03",
            "title": "Review Prompt Isolation",
            "execution_mode": "code_change",
            "owned_files": ["src/review_target.py"],
        },
        "\n# WP03\n",
    )
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=mission_slug,
            mission_id="01KQKV85CANONICAL000000000",
            mission_branch=mission_branch,
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=("WP03",),
                    write_scope=("src/**",),
                    predicted_surfaces=("src",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-05-02T09:00:00Z",
            computed_from="test",
        ),
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed mission")
    _git(repo, "branch", mission_branch)

    worktree = repo / ".worktrees" / f"{mission_slug}-lane-a"
    _git(repo, "worktree", "add", "-b", lane_branch, str(worktree), mission_branch)
    (worktree / "src").mkdir()
    (worktree / "src" / "review_target.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(worktree, "add", "src/review_target.py")
    _git(worktree, "commit", "-m", "feat(WP03): add review target")

    wp_frontmatter = (tasks_dir / "WP03-review-prompt-isolation.md").read_text(encoding="utf-8")
    ctx = _resolve_review_context(worktree, repo, mission_slug, "WP03", wp_frontmatter)

    reconstructed_wrong_ref = f"kitty/mission-{mission_slug}"
    assert reconstructed_wrong_ref == "kitty/mission-mission-canonical-refs"
    assert ctx["mission_branch"] == mission_branch
    assert ctx["base_ref"] == mission_branch
    assert ctx["base_branch"] == mission_branch
    assert ctx["lane_branch"] == lane_branch
    assert reconstructed_wrong_ref not in f"git diff {ctx['base_ref']}..{ctx['lane_branch']}"
