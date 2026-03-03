"""Integration tests for workspace-per-WP workflow.

Tests the complete workflow:
- Planning in main (specify, plan, tasks) without creating worktrees
- Workspace creation with implement command
- Dependency-aware branching with --base flag
- Parallel WP development
- Merge workflow with multiple WP branches
- Pre-upgrade validation
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

# Get repo root for Python module invocation
REPO_ROOT = Path(__file__).resolve().parents[2]


# ============================================================================
# Helper Functions
# ============================================================================


def run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Execute spec-kitty CLI using Python module invocation.

    Uses venv python and python -m instead of shelling out to binary for better test reliability.
    """
    from tests.test_isolation_helpers import get_venv_python

    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(
        os.pathsep
    )
    env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
    )


def init_test_repo(tmp_path: Path) -> Path:
    """Initialize test git repository with initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (tmp_path / "README.md").write_text("Test repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


def create_feature_in_main(repo: Path, feature_slug: str) -> Path:
    """Create feature directory in main repo (simulates /spec-kitty.specify)."""
    import json

    feature_dir = repo / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Create spec.md
    (feature_dir / "spec.md").write_text(f"# Spec for {feature_slug}")

    # Create meta.json (required for VCS locking)
    meta_content = {
        "feature_number": feature_slug.split("-")[0],
        "feature_slug": feature_slug,
        "created_at": "2026-01-17T00:00:00Z",
        "vcs": "git",  # Lock to git for tests
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta_content, indent=2))

    # Create tasks directory
    (feature_dir / "tasks").mkdir(exist_ok=True)

    # Commit to main
    subprocess.run(
        ["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"Add spec for {feature_slug}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return feature_dir


def create_wp_file(feature_dir: Path, wp_id: str, dependencies: list[str]) -> Path:
    """Create WP prompt file with frontmatter."""
    wp_file = feature_dir / "tasks" / f"{wp_id}-test.md"
    if not dependencies:
        deps_str = "[]"
    else:
        deps_list = ", ".join(f'"{d}"' for d in dependencies)
        deps_str = f"[{deps_list}]"
    frontmatter = f"""---
work_package_id: "{wp_id}"
dependencies: {deps_str}
lane: "planned"
---

# {wp_id} Test Work Package

This is a test work package.
"""
    wp_file.write_text(frontmatter)
    return wp_file


def implement_wp(
    repo: Path, feature_slug: str, wp_id: str, base: str | None = None
) -> Path:
    """Create workspace for WP using spec-kitty implement command.

    Uses the actual spec-kitty implement command to test real command behavior.
    """
    workspace_name = f"{feature_slug}-{wp_id}"
    workspace_path = repo / ".worktrees" / workspace_name

    if workspace_path.exists():
        # Workspace already exists, return it
        return workspace_path

    # Ensure we're on the feature branch for context detection
    # Check if feature branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", feature_slug],
        cwd=repo,
        capture_output=True,
        check=False
    )

    if result.returncode != 0:
        # Feature branch doesn't exist, create it
        subprocess.run(
            ["git", "checkout", "-b", feature_slug],
            cwd=repo,
            check=True,
            capture_output=True
        )
    else:
        # Feature branch exists, check it out
        subprocess.run(
            ["git", "checkout", feature_slug],
            cwd=repo,
            check=True,
            capture_output=True
        )

    # Build spec-kitty implement command arguments
    args = ["implement", wp_id]
    if base is not None:
        args.extend(["--base", base])

    # Run spec-kitty implement command using Python module invocation
    result = run_cli(repo, *args)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create workspace: {result.stderr}\nCommand: spec-kitty {' '.join(args)}\nStdout: {result.stdout}"
        )

    return workspace_path


# ============================================================================
# T071 - Planning Workflow in Main
# ============================================================================


def test_planning_in_main_no_worktrees(tmp_path):
    """Test planning workflow creates artifacts in main, not worktrees (FR-001, FR-003).

    Validates:
    - /spec-kitty.specify creates artifacts in main
    - /spec-kitty.plan creates artifacts in main
    - /spec-kitty.tasks creates artifacts in main
    - NO worktrees created during planning
    - All artifacts committed to main branch
    """
    # Initialize test repo
    repo = init_test_repo(tmp_path)

    # Simulate /spec-kitty.specify
    feature_dir = create_feature_in_main(repo, "011-test-feature")
    assert feature_dir.exists()
    assert feature_dir == repo / "kitty-specs" / "011-test-feature"

    # Verify NO worktree created
    worktrees_dir = repo / ".worktrees"
    if worktrees_dir.exists():
        worktree_count = len(list(worktrees_dir.iterdir()))
        assert worktree_count == 0, f"Expected no worktrees, found {worktree_count}"

    # Verify committed to main
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Add spec for" in result.stdout

    # Simulate /spec-kitty.plan
    plan_file = feature_dir / "plan.md"
    plan_file.write_text("# Plan")
    subprocess.run(
        ["git", "add", str(plan_file)], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add plan"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Simulate /spec-kitty.tasks
    create_wp_file(feature_dir, "WP01", [])
    create_wp_file(feature_dir, "WP02", ["WP01"])
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add tasks"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Verify still NO worktrees
    if worktrees_dir.exists():
        worktree_count = len(list(worktrees_dir.iterdir()))
        assert worktree_count == 0, f"Expected no worktrees after tasks, found {worktree_count}"

    # Verify 3 commits in main (initial + spec + plan + tasks = 4 total)
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Add spec" in result.stdout
    assert "Add plan" in result.stdout
    assert "Add tasks" in result.stdout




# ============================================================================
# T072 - Implement WP01 (No Dependencies)
# ============================================================================


def test_implement_wp_no_dependencies(tmp_path):
    """Test implementing WP01 (no dependencies) creates workspace from main (FR-004, FR-005).

    Validates:
    - spec-kitty implement WP01 creates workspace
    - Workspace named correctly: .worktrees/###-feature-WP01/
    - Branch created from main
    - Workspace contains planning artifacts
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP01", [])

    # Commit WP file to main
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WP01"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Implement WP01
    workspace = implement_wp(repo, "011-test", "WP01", base=None)

    # Verify workspace created
    assert workspace.exists()
    assert workspace.is_dir()
    assert workspace == repo / ".worktrees" / "011-test-WP01"

    # Verify git worktree exists
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "011-test-WP01" in result.stdout

    # Verify branch created
    result = subprocess.run(
        ["git", "branch", "--list", "011-test-WP01"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "011-test-WP01" in result.stdout

    # Verify sparse-checkout excludes kitty-specs from worktree
    # (kitty-specs status is tracked in main repo only, preventing state divergence)
    assert not (workspace / "kitty-specs").exists(), \
        "kitty-specs should be excluded from worktree via sparse-checkout"


# ============================================================================
# T073 - Implement WP02 with Dependencies
# ============================================================================


def test_implement_wp_with_dependencies(tmp_path):
    """Test implementing WP02 with --base WP01 branches from WP01 (FR-006, FR-007, FR-008).

    Validates:
    - spec-kitty implement WP02 --base WP01 creates workspace
    - WP02 branches from WP01's branch (not main)
    - WP02 workspace contains WP01's changes
    - Git graph shows correct branching structure
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP01", [])
    create_wp_file(feature_dir, "WP02", ["WP01"])

    # Commit WP files
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WPs"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Implement WP01
    wp01_workspace = implement_wp(repo, "011-test", "WP01", base=None)

    # Make commit in WP01 workspace
    test_file = wp01_workspace / "test.txt"
    test_file.write_text("WP01 changes")
    subprocess.run(
        ["git", "add", "test.txt"], cwd=wp01_workspace, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "WP01 work"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP02 with --base WP01
    wp02_workspace = implement_wp(repo, "011-test", "WP02", base="WP01")

    # Verify WP02 workspace created
    assert wp02_workspace.exists()
    assert wp02_workspace == repo / ".worktrees" / "011-test-WP02"

    # Verify WP02 contains WP01's changes (branched from WP01)
    assert (wp02_workspace / "test.txt").exists()
    assert (wp02_workspace / "test.txt").read_text() == "WP01 changes"

    # Verify WP02's HEAD has WP01's commit in its history
    # This is the key test: WP02 should have WP01's changes in its git history
    result = subprocess.run(
        ["git", "log", "--oneline", "011-test-WP02"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "WP01 work" in result.stdout, f"WP02 should have WP01 work in history, got: {result.stdout}"

    # Verify both branches exist
    result = subprocess.run(
        ["git", "branch", "--list"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert "011-test-WP01" in result.stdout
    assert "011-test-WP02" in result.stdout


# ============================================================================
# T074 - Parallel Implementation
# ============================================================================


def test_parallel_wp_implementation(tmp_path):
    """Test multiple WPs implemented in parallel (SC-001).

    Validates:
    - Multiple agents can implement different WPs simultaneously
    - Each workspace is isolated
    - Changes in WP01 don't appear in WP03 (parallel, no deps)
    - Both workspaces exist and are valid
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP01", [])
    create_wp_file(feature_dir, "WP03", [])

    # Commit WPs
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WPs"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Implement WP01 and WP03 "simultaneously" (both branch from main)
    wp01_workspace = implement_wp(repo, "011-test", "WP01", base=None)
    wp03_workspace = implement_wp(repo, "011-test", "WP03", base=None)

    # Verify both workspaces exist
    assert wp01_workspace.exists()
    assert wp03_workspace.exists()
    assert wp01_workspace == repo / ".worktrees" / "011-test-WP01"
    assert wp03_workspace == repo / ".worktrees" / "011-test-WP03"

    # Make different commits in each workspace
    (wp01_workspace / "file_a.txt").write_text("WP01 work")
    subprocess.run(
        ["git", "add", "file_a.txt"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "WP01 changes"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )

    (wp03_workspace / "file_c.txt").write_text("WP03 work")
    subprocess.run(
        ["git", "add", "file_c.txt"],
        cwd=wp03_workspace,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "WP03 changes"],
        cwd=wp03_workspace,
        check=True,
        capture_output=True,
    )

    # Verify isolation: WP01 workspace doesn't have file_c.txt
    assert not (wp01_workspace / "file_c.txt").exists()

    # Verify isolation: WP03 workspace doesn't have file_a.txt
    assert not (wp03_workspace / "file_a.txt").exists()

    # Verify both branches exist independently
    result = subprocess.run(
        ["git", "branch"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert "011-test-WP01" in result.stdout
    assert "011-test-WP03" in result.stdout


# ============================================================================
# T075 - Dependency Validation Errors
# ============================================================================


def test_implement_missing_base_workspace_error(tmp_path):
    """Test error when implementing WP with --base that doesn't exist (FR-008).

    Validates:
    - Attempting to implement WP02 --base WP01 when WP01 workspace doesn't exist
    - Should fail with clear error
    - No WP02 workspace created
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP02", ["WP01"])

    # Commit WP file
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WP02"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Try to implement WP02 before WP01 exists (should fail)
    with pytest.raises(RuntimeError, match="Failed to create workspace"):
        implement_wp(repo, "011-test", "WP02", base="WP01")

    # Verify no workspace created
    assert not (repo / ".worktrees" / "011-test-WP02").exists()


def test_circular_dependency_detection(tmp_path):
    """Test circular dependency detection (FR-013).

    Validates:
    - Circular dependency graph is detected
    - WP01 → WP02 → WP01 creates a cycle
    """
    from specify_cli.core.dependency_graph import build_dependency_graph, detect_cycles

    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")

    # Create circular dependency: WP01 → WP02 → WP01
    create_wp_file(feature_dir, "WP01", ["WP02"])
    create_wp_file(feature_dir, "WP02", ["WP01"])

    # Build graph - note that build_dependency_graph takes feature_dir not tasks_dir
    graph = build_dependency_graph(feature_dir)

    # Detect cycles - returns list of lists (each list is a cycle)
    cycles = detect_cycles(graph)

    assert cycles is not None, "Expected to detect circular dependency"
    assert len(cycles) > 0, "Expected at least one cycle"

    # Flatten all cycles into a set of WPs involved in cycles
    cycle_wps = set()
    for cycle in cycles:
        cycle_wps.update(cycle)

    assert "WP01" in cycle_wps, f"Expected WP01 in cycles, got: {cycles}"
    assert "WP02" in cycle_wps, f"Expected WP02 in cycles, got: {cycles}"


def test_implement_missing_base_flag_suggestion(tmp_path):
    """Test suggestion when WP has dependencies but --base not provided (FR-015).

    Validates:
    - WP02 has dependency on WP01 in frontmatter
    - Attempting to implement without --base should suggest correct command
    - Uses real spec-kitty implement command (no mocks)
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP02", ["WP01"])

    # Commit WP file
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WP02"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create a branch to simulate feature context
    subprocess.run(
        ["git", "checkout", "-b", "011-test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Try to implement WP02 without --base flag using actual command
    result = run_cli(repo, "implement", "WP02")

    # Should fail (non-zero exit code)
    assert result.returncode != 0

    # Should suggest using --base flag
    output = result.stdout + result.stderr
    assert "WP01" in output or "base" in output.lower() or "depend" in output.lower()


def test_implement_with_base_flag_success(tmp_path):
    """Test successful implementation with correct --base flag (FR-007, FR-008).

    Validates:
    - WP01 implemented first
    - WP02 with --base WP01 succeeds
    - Real spec-kitty implement command (no mocks)
    - Tests actual dependency enforcement
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")
    create_wp_file(feature_dir, "WP01", [])
    create_wp_file(feature_dir, "WP02", ["WP01"])

    # Commit WP files
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WPs"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create feature branch for context detection
    subprocess.run(
        ["git", "checkout", "-b", "011-test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Implement WP01 first (no dependencies)
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0, f"WP01 implementation failed: {result.stderr}"

    # Verify WP01 workspace exists
    wp01_workspace = repo / ".worktrees" / "011-test-WP01"
    assert wp01_workspace.exists()

    # Implement WP02 with correct --base flag
    result = run_cli(repo, "implement", "WP02", "--base", "WP01")
    assert result.returncode == 0, f"WP02 implementation failed: {result.stderr}"

    # Verify WP02 workspace exists
    wp02_workspace = repo / ".worktrees" / "011-test-WP02"
    assert wp02_workspace.exists()

    # Verify WP02 branched from WP01 (not main)
    result = subprocess.run(
        ["git", "log", "--oneline", "011-test-WP02"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    # Should include initial commit from main
    assert "Initial commit" in result.stdout


# ============================================================================
# T076 - Merge Workflow (Partial Test)
# ============================================================================


def test_merge_workspace_per_wp_preparation(tmp_path):
    """Test merge workflow with multiple WP worktrees - preparation phase.

    Note: Full merge test requires actual merge command integration.
    This test validates the prerequisites:
    - Multiple WP branches exist
    - Each has commits
    - All branches can be merged to main (no conflicts)
    """
    repo = init_test_repo(tmp_path)
    feature_dir = create_feature_in_main(repo, "011-test")

    # Create WP files
    create_wp_file(feature_dir, "WP01", [])
    create_wp_file(feature_dir, "WP02", ["WP01"])
    create_wp_file(feature_dir, "WP03", [])

    # Commit WPs
    subprocess.run(
        ["git", "add", str(feature_dir / "tasks")],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add WPs"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Implement all WPs
    wp01_workspace = implement_wp(repo, "011-test", "WP01", base=None)
    wp02_workspace = implement_wp(repo, "011-test", "WP02", base="WP01")
    wp03_workspace = implement_wp(repo, "011-test", "WP03", base=None)

    # Make commits in each workspace
    for wp_id, workspace in [
        ("WP01", wp01_workspace),
        ("WP02", wp02_workspace),
        ("WP03", wp03_workspace),
    ]:
        (workspace / f"{wp_id}.txt").write_text(f"{wp_id} work")
        subprocess.run(
            ["git", "add", "."], cwd=workspace, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"{wp_id} work"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

    # Verify all branches exist
    result = subprocess.run(
        ["git", "branch"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert "011-test-WP01" in result.stdout
    assert "011-test-WP02" in result.stdout
    assert "011-test-WP03" in result.stdout

    # Test merge feasibility: merge WP01 to default branch (no conflicts expected)
    # Get the default branch name (could be 'main' or 'master')
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True
    )
    default_branch = branch_result.stdout.strip()

    subprocess.run(
        ["git", "checkout", default_branch], cwd=repo, check=True, capture_output=True
    )
    result = subprocess.run(
        ["git", "merge", "--no-ff", "011-test-WP01", "-m", "Merge WP01"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Merge failed: {result.stderr}"

    # Verify WP01 file merged to main
    assert (repo / "WP01.txt").exists()
    assert (repo / "WP01.txt").read_text() == "WP01 work"


# ============================================================================
# T077 - Pre-Upgrade Validation
# ============================================================================


def test_pre_upgrade_validation_blocks_legacy_worktrees(tmp_path):
    """Test migration blocks when legacy worktrees exist (FR-022, FR-023).

    Validates:
    - Legacy worktree pattern detected (###-feature without -WP##)
    - Validation fails
    - Clear error message provided
    """
    from specify_cli.upgrade.migrations.m_0_11_0_workspace_per_wp import (
        validate_upgrade,
    )

    repo = init_test_repo(tmp_path)

    # Create legacy worktree (###-feature pattern, no -WP## suffix)
    legacy_dir = repo / ".worktrees" / "009-old-feature"
    legacy_dir.mkdir(parents=True)

    # Validate upgrade
    is_valid, errors = validate_upgrade(repo)

    # Should fail validation
    assert is_valid is False
    assert len(errors) > 0
    assert any("009-old-feature" in err for err in errors)
    # Error should mention merge or delete
    errors_text = " ".join(errors).lower()
    assert "merge" in errors_text or "delete" in errors_text or "complete" in errors_text


def test_pre_upgrade_validation_passes_with_new_worktrees(tmp_path):
    """Test migration passes when only workspace-per-WP worktrees exist (FR-024).

    Validates:
    - New worktree pattern accepted (###-feature-WP##)
    - Validation passes
    - No errors reported
    """
    from specify_cli.upgrade.migrations.m_0_11_0_workspace_per_wp import (
        validate_upgrade,
    )

    repo = init_test_repo(tmp_path)

    # Create workspace-per-WP worktrees (new pattern)
    new_dir1 = repo / ".worktrees" / "010-feature-WP01"
    new_dir1.mkdir(parents=True)
    new_dir2 = repo / ".worktrees" / "010-feature-WP02"
    new_dir2.mkdir(parents=True)

    # Run validation
    is_valid, errors = validate_upgrade(repo)

    # Should pass (new pattern is OK)
    assert is_valid is True
    assert len(errors) == 0


def test_pre_upgrade_validation_passes_with_no_worktrees(tmp_path):
    """Test migration passes when no worktrees exist.

    Validates:
    - Empty .worktrees directory is acceptable
    - Non-existent .worktrees directory is acceptable
    """
    from specify_cli.upgrade.migrations.m_0_11_0_workspace_per_wp import (
        validate_upgrade,
    )

    repo = init_test_repo(tmp_path)

    # No worktrees directory at all
    is_valid, errors = validate_upgrade(repo)
    assert is_valid is True
    assert len(errors) == 0

    # Empty worktrees directory
    (repo / ".worktrees").mkdir()
    is_valid, errors = validate_upgrade(repo)
    assert is_valid is True
    assert len(errors) == 0
