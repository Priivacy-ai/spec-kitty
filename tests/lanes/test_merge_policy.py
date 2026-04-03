"""Tests for lane merge policy enforcement.

Verifies that lane branches cannot bypass the mission integration branch
and merge directly to the target (e.g., main).
"""

from specify_cli.cli.commands.merge import detect_worktree_structure


def test_lanes_json_triggers_lane_based_structure(tmp_path):
    """When lanes.json exists, detect_worktree_structure returns 'lane-based'.

    This ensures the merge command dispatches to the two-tier lane merge flow
    (lane→mission→target) rather than the legacy WP-per-worktree merge that
    would merge directly to the target branch.
    """
    # Create minimal repo structure
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True, check=True)
    (tmp_path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=True)

    # Create kitty-specs with lanes.json
    feature_dir = tmp_path / "kitty-specs" / "010-feat"
    feature_dir.mkdir(parents=True)
    (feature_dir / "lanes.json").write_text('{"version": 1}')

    result = detect_worktree_structure(tmp_path, "010-feat")
    assert result == "lane-based"


def test_no_lanes_json_does_not_trigger_lane_based(tmp_path):
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True, check=True)
    (tmp_path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=True)

    feature_dir = tmp_path / "kitty-specs" / "010-feat"
    feature_dir.mkdir(parents=True)
    # No lanes.json

    result = detect_worktree_structure(tmp_path, "010-feat")
    assert result != "lane-based"
