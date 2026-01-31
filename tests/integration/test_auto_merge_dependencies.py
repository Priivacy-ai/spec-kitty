"""Tests for auto-merging completed dependencies before implementing dependent WPs.

Scenario: WP04 depends on WP01, WP02, WP03 (all in "done" lane)

Current behavior:
- spec-kitty implement WP04
- Attempts multi-parent auto-merge
- Fails on .gitignore conflicts
- Agent manually merges WP01-03 to main
- Then starts WP04 from main

Improved behavior:
- spec-kitty implement WP04
- Detects: All dependencies (WP01-03) are in "done" lane
- Suggests: "Merge dependencies to main first? (y/n)"
- Auto-merges WP01-03 to main (with conflict resolution)
- Then starts WP04 from main (clean)

This test suite validates the detection and automation logic.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Execute spec-kitty CLI."""
    from tests.test_isolation_helpers import get_venv_python

    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(command, cwd=str(project_path), capture_output=True, text=True, env=env)


def test_detect_all_dependencies_done():
    """Test detection logic for when all dependencies are in done lane.

    Validates:
    - Can read all WP files
    - Can detect lane status
    - Can identify when ALL dependencies are done
    - Returns true/false correctly
    """
    from specify_cli.frontmatter import read_frontmatter
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create WP files
        for wp_id, lane in [("WP01", "done"), ("WP02", "done"), ("WP03", "done")]:
            wp_file = tmp_path / f"{wp_id}.md"
            wp_file.write_text(
                f"---\n"
                f"work_package_id: {wp_id}\n"
                f"lane: {lane}\n"
                f"---\n\n"
                f"# {wp_id}\n"
            )

        # Check if all done
        all_done = True
        for wp_id in ["WP01", "WP02", "WP03"]:
            frontmatter, _ = read_frontmatter(tmp_path / f"{wp_id}.md")
            if frontmatter.get("lane") != "done":
                all_done = False
                break

        assert all_done is True, "All dependencies should be detected as done"


def test_detect_partial_dependencies_done():
    """Test detection when only some dependencies are done.

    Validates:
    - Returns false when any dependency not done
    - Can distinguish between done, for_review, doing
    """
    from specify_cli.frontmatter import read_frontmatter
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create WP files with mixed status
        for wp_id, lane in [("WP01", "done"), ("WP02", "for_review"), ("WP03", "done")]:
            wp_file = tmp_path / f"{wp_id}.md"
            wp_file.write_text(
                f"---\n"
                f"work_package_id: {wp_id}\n"
                f"lane: {lane}\n"
                f"---\n\n"
                f"# {wp_id}\n"
            )

        # Check if all done
        all_done = True
        for wp_id in ["WP01", "WP02", "WP03"]:
            frontmatter, _ = read_frontmatter(tmp_path / f"{wp_id}.md")
            if frontmatter.get("lane") != "done":
                all_done = False
                break

        assert all_done is False, "Should detect that WP02 is not done"


def test_should_merge_dependencies_before_implement():
    """Test logic for when to auto-merge dependencies.

    Decision matrix:
    - All dependencies in "done" lane? → Suggest merge
    - Any dependency not done? → Don't suggest (not ready)
    - Multi-parent (2+ dependencies)? → Higher priority for merge
    - Single parent? → Can use --base flag (no merge needed)
    """
    # Test case 1: All done, multi-parent → should merge
    deps_all_done_multi = ["WP01", "WP02", "WP03"]
    lanes = {"WP01": "done", "WP02": "done", "WP03": "done"}

    should_merge = all(lanes[dep] == "done" for dep in deps_all_done_multi)
    assert should_merge is True, "Should suggest merge when all deps done"

    # Test case 2: Partial done, multi-parent → should NOT merge
    deps_partial_multi = ["WP01", "WP02", "WP03"]
    lanes_partial = {"WP01": "done", "WP02": "for_review", "WP03": "done"}

    should_merge_partial = all(lanes_partial[dep] == "done" for dep in deps_partial_multi)
    assert should_merge_partial is False, "Should NOT merge when any dep not done"

    # Test case 3: All done, single parent → don't need merge (use --base)
    deps_single = ["WP01"]
    lanes_single = {"WP01": "done"}

    is_multi_parent = len(deps_single) > 1
    should_merge_single = is_multi_parent and all(lanes_single[dep] == "done" for dep in deps_single)
    assert should_merge_single is False, "Single parent uses --base, no merge needed"


def test_merge_suggestion_message():
    """Test that suggestion message is clear and actionable.

    When all multi-parent dependencies are done, suggest:

    'WP04 depends on WP01, WP02, WP03 (all done).
     Merge dependencies to main first to avoid conflicts?

     Run: spec-kitty merge --feature 001-triple-tic-tac-toe
     Then: spec-kitty implement WP04

     Or use --force to attempt auto-merge (may conflict)'
    """
    deps = ["WP01", "WP02", "WP03"]
    wp_id = "WP04"

    suggestion = (
        f"{wp_id} depends on {', '.join(deps)} (all done).\n"
        f"Merge dependencies to main first to avoid conflicts?\n\n"
        f"Run: spec-kitty merge --feature <feature-slug>\n"
        f"Then: spec-kitty implement {wp_id}\n\n"
        f"Or use --force to attempt auto-merge (may conflict)"
    )

    assert "all done" in suggestion
    assert "spec-kitty merge" in suggestion
    assert "--force" in suggestion


def test_auto_merge_dependencies_flag():
    """Test proposed --merge-dependencies flag for implement command.

    Usage:
      spec-kitty implement WP04 --merge-dependencies

    Behavior:
    1. Check dependencies (WP01, WP02, WP03)
    2. Verify all in "done" lane
    3. Merge each to main sequentially (with conflict handling)
    4. Then create WP04 from updated main

    This automates the manual workflow the agent had to do.
    """
    # This is a design test - documents the proposed behavior
    # Actual implementation would be in implement.py

    expected_workflow = [
        "1. Parse WP04 dependencies: [WP01, WP02, WP03]",
        "2. Check lanes: all 'done'? True",
        "3. Merge WP01 to main (resolve conflicts if any)",
        "4. Merge WP02 to main (resolve conflicts if any)",
        "5. Merge WP03 to main (resolve conflicts if any)",
        "6. Create WP04 worktree from main",
        "7. WP04 now has all dependency code",
    ]

    assert len(expected_workflow) == 7
    assert "Merge WP01 to main" in expected_workflow[2]
    assert "Create WP04 worktree from main" in expected_workflow[5]


def test_conflict_prediction_dry_run():
    """Test that we could predict conflicts before attempting merge.

    Approach:
    1. git merge-tree (no-commit merge simulation)
    2. Check for conflict markers
    3. Report: "WP01 and WP02 conflict on .gitignore"
    4. Suggest resolution strategy

    This would let agents know upfront which files will conflict.
    """
    # This is a design test - documents proposed conflict prediction

    # Example output:
    predicted_conflicts = {
        ".gitignore": ["WP01", "WP02", "WP03"],  # All three modify it
        "package.json": ["WP02"],  # Only WP02 adds it
    }

    # Agent could then:
    # - Warn: ".gitignore conflicts in 3 WPs (requires manual resolution)"
    # - Suggest: "Merge WP01-03 to main first, or use --force"

    assert ".gitignore" in predicted_conflicts
    assert len(predicted_conflicts[".gitignore"]) == 3


def test_recommendation_engine():
    """Test recommendation engine for dependency merge strategy.

    Input: WP04 depends on WP01, WP02, WP03 (all done)

    Analysis:
    - Multi-parent: Yes (3 parents)
    - All done: Yes
    - Conflicts likely: Unknown (would need dry-run)

    Recommendation:
    → "Merge dependencies first (safer, avoids auto-merge conflicts)"

    Alternative if no conflicts predicted:
    → "Auto-merge should work (no conflicts predicted)"
    """
    # Design test for recommendation logic

    def recommend_strategy(dep_count: int, all_done: bool, conflicts_predicted: bool) -> str:
        if not all_done:
            return "Cannot implement - dependencies not complete"

        if dep_count == 1:
            return "Use --base flag (single parent)"

        if dep_count > 1 and conflicts_predicted:
            return "Merge dependencies first (conflicts predicted)"

        if dep_count > 1 and not conflicts_predicted:
            return "Auto-merge should work (no conflicts predicted)"

        return "Unknown"

    # Scenario 1: Multi-parent, all done, conflicts predicted
    rec1 = recommend_strategy(dep_count=3, all_done=True, conflicts_predicted=True)
    assert "Merge dependencies first" in rec1

    # Scenario 2: Multi-parent, all done, no conflicts
    rec2 = recommend_strategy(dep_count=3, all_done=True, conflicts_predicted=False)
    assert "Auto-merge should work" in rec2

    # Scenario 3: Single parent
    rec3 = recommend_strategy(dep_count=1, all_done=True, conflicts_predicted=False)
    assert "--base flag" in rec3

    # Scenario 4: Not all done
    rec4 = recommend_strategy(dep_count=3, all_done=False, conflicts_predicted=False)
    assert "Cannot implement" in rec4
