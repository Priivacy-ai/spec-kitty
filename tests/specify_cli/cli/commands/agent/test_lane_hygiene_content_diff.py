"""Lane-hygiene guard content-diff vs planning-tip (WP06 / FR-007 / #2274).

The guard ``_list_wp_branch_mission_specs_changes`` must compare kitty-specs/
files by CONTENT against the planning-branch tip, not by commit-history
(merge-base) diff.

Background: after a planning-branch rebase the lane branch shares only an
ancient merge-base with the planning branch, so a merge-base diff surfaces any
kitty-specs/ file the lane branch touched — even when that file is
byte-identical to the planning tip.  This is a false positive that blocks
``move-task`` without ``--force`` and inflates ``force_count``.

Scenarios covered:

  T024 — RED (pre-fix): lane branch with a kitty-specs/ file byte-identical to
         the planning tip but with an ancient merge-base is FLAGGED (false
         positive).  The test asserts the desired behaviour (not flagged) and
         therefore FAILS on pre-fix code.
  T025 — content re-check against planning tip drops the byte-identical file
         after the WP06 fix.
  T026 — genuinely-divergent kitty-specs/ file IS still flagged after the fix;
         the guard's real signal is preserved.

All tests exercise ``_list_wp_branch_mission_specs_changes`` directly through
the real entry point (no monkeypatching of git).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.tasks import _list_wp_branch_mission_specs_changes

pytestmark = [pytest.mark.unit, pytest.mark.git_repo, pytest.mark.regression]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with standard test config."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test Runner")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------


def _build_rebase_scenario(
    tmp_path: Path,
    *,
    lane_content: str = "spec content\n",
    planning_content: str | None = None,
) -> tuple[Path, str]:
    """Simulate a post-planning-branch-rebase setup.

    Layout::

        A (main / anchor) ──┬── planning: A → B  (adds kitty-specs/spec.md)
                            │
                            └── lane:     A → C  (adds kitty-specs/spec.md)

    ``planning`` and ``lane`` diverge from the same anchor ``A``, so
    ``merge-base(lane HEAD, planning)`` == ``A``.  When
    ``planning_content is None`` both branches use ``lane_content``, making the
    file byte-identical across the two branch tips — the false-positive scenario.

    Returns ``(repo_path, planning_branch_name)``.
    """
    if planning_content is None:
        planning_content = lane_content

    repo = _init_repo(tmp_path)

    # Anchor commit — no kitty-specs yet
    (repo / "README.md").write_text("anchor\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "anchor")

    anchor_sha = subprocess.run(
        ["git", "rev-parse", "main"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()

    # Planning branch: add kitty-specs/spec.md with planning_content
    _git(repo, "checkout", "-q", "-b", "planning")
    ks_dir = repo / "kitty-specs" / "test-mission"
    ks_dir.mkdir(parents=True)
    (ks_dir / "spec.md").write_text(planning_content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "planning: add kitty-specs")

    # Lane branch: forked from the ANCHOR commit (simulates old fork point /
    # a planning-branch rebase that moved the base forward)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-q", "-b", "lane")
    lane_ks_dir = repo / "kitty-specs" / "test-mission"
    lane_ks_dir.mkdir(parents=True)
    (lane_ks_dir / "spec.md").write_text(lane_content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "lane: add kitty-specs")

    # Verify invariant: merge-base(lane HEAD, planning) == anchor, not planning tip
    mb = subprocess.run(
        ["git", "merge-base", "HEAD", "planning"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert mb == anchor_sha, (
        f"Scenario invariant violated: expected merge-base == anchor ({anchor_sha!r}), "
        f"got {mb!r}"
    )

    return repo, "planning"


# ---------------------------------------------------------------------------
# T024 / T025: byte-identical file after simulated rebase
# ---------------------------------------------------------------------------


class TestByteIdenticalNotFlagged:
    """T024 + T025: a kitty-specs/ file byte-identical to the planning tip must
    not be flagged, even when the merge-base is ancient.

    On pre-fix code (merge-base history diff only) this test FAILS (RED) because
    the guard surfaces the file.  After the WP06 content re-check it passes
    (GREEN).
    """

    def test_t024_byte_identical_file_is_not_flagged(self, tmp_path: Path) -> None:
        """T024 (RED pre-fix / GREEN post-fix): byte-identical kitty-specs/ not flagged.

        This is the primary red-first regression test for FR-007.  The lane
        branch has kitty-specs/test-mission/spec.md with the same content as
        the planning tip, but the merge-base is an ancient anchor commit.

        Pre-fix behaviour: the guard uses ``git diff merge-base..HEAD`` and flags
        the file (false positive) → assertion fails (RED).

        Post-fix behaviour: the content re-check detects an empty diff vs the
        planning tip and drops the file → assertion passes (GREEN).
        """
        repo, planning = _build_rebase_scenario(tmp_path, lane_content="spec content\n")

        flagged = _list_wp_branch_mission_specs_changes(repo, planning)

        assert flagged == [], (
            f"False positive: byte-identical kitty-specs/ file was flagged after rebase. "
            f"Flagged paths: {flagged!r}"
        )

    def test_t025_no_force_count_inflation_for_identical_file(self, tmp_path: Path) -> None:
        """T025: byte-identical file returns empty list (no force_count pressure).

        Confirms the content re-check produces an empty result, meaning no
        ``--force`` requirement is triggered for the false-positive case.
        """
        repo, planning = _build_rebase_scenario(
            tmp_path, lane_content="# Mission spec\n\nContent here.\n"
        )

        flagged = _list_wp_branch_mission_specs_changes(repo, planning)

        assert len(flagged) == 0, (
            f"Expected empty list (no force_count inflation), got {flagged!r}"
        )


# ---------------------------------------------------------------------------
# T026: genuinely-divergent file is still flagged
# ---------------------------------------------------------------------------


class TestGenuinelyDivergentStillFlagged:
    """T026: a kitty-specs/ file that genuinely diverges from the planning tip
    must still be flagged regardless of the content re-check.

    This asserts the guard's real signal is preserved after the WP06 fix.
    """

    def test_t026_divergent_content_is_flagged(self, tmp_path: Path) -> None:
        """T026: genuinely-divergent kitty-specs/ file is flagged after fix.

        The lane branch has different content from the planning tip.  The
        content re-check finds a non-empty diff and keeps the file in the
        flagged list.  This must hold both pre-fix and post-fix.
        """
        repo, planning = _build_rebase_scenario(
            tmp_path,
            lane_content="# Lane diverged\n\nThis content differs.\n",
            planning_content="# Planning tip\n\nOriginal content.\n",
        )

        flagged = _list_wp_branch_mission_specs_changes(repo, planning)

        assert len(flagged) > 0, (
            "Guard neutered: genuinely-divergent kitty-specs/ file was NOT flagged. "
            "The guard must retain its signal for real divergence."
        )
        assert any("spec.md" in p for p in flagged), (
            f"Expected 'spec.md' among flagged paths, got {flagged!r}"
        )

    def test_t026_mixed_files_only_divergent_flagged(self, tmp_path: Path) -> None:
        """T026 (extended): when one file is identical and one diverges, only the
        divergent file appears in the result.
        """
        repo = _init_repo(tmp_path)

        # Anchor commit
        (repo / "README.md").write_text("anchor\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "anchor")

        anchor_sha = subprocess.run(
            ["git", "rev-parse", "main"],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout.strip()

        # Planning branch: add two kitty-specs files
        _git(repo, "checkout", "-q", "-b", "planning")
        ks_dir = repo / "kitty-specs" / "mission-x"
        ks_dir.mkdir(parents=True)
        (ks_dir / "spec.md").write_text("shared content\n", encoding="utf-8")
        (ks_dir / "plan.md").write_text("planning plan\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "planning: add two files")

        # Lane branch: identical spec.md, diverged plan.md
        _git(repo, "checkout", "-q", "main")
        _git(repo, "checkout", "-q", "-b", "lane")
        lane_ks_dir = repo / "kitty-specs" / "mission-x"
        lane_ks_dir.mkdir(parents=True)
        (lane_ks_dir / "spec.md").write_text("shared content\n", encoding="utf-8")  # identical
        (lane_ks_dir / "plan.md").write_text("lane-modified plan\n", encoding="utf-8")  # diverged
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "lane: add files (spec identical, plan diverged)")

        # Verify merge-base is the anchor
        mb = subprocess.run(
            ["git", "merge-base", "HEAD", "planning"],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert mb == anchor_sha

        flagged = _list_wp_branch_mission_specs_changes(repo, "planning")

        flagged_names = [Path(p).name for p in flagged]
        assert "plan.md" in flagged_names, (
            f"Diverged file 'plan.md' should be flagged, got {flagged!r}"
        )
        assert "spec.md" not in flagged_names, (
            f"Identical file 'spec.md' should NOT be flagged, got {flagged!r}"
        )
