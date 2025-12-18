---
work_package_id: "WP05"
subtasks: ["T070", "T071", "T072", "T073", "T074", "T075"]
title: "Final Feature Lifecycle Commands"
phase: "Phase 5 - Completion Commands (Stream D)"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "200"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-18T01:30:00Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt rewritten to correct scope (was incorrectly targeting meta-scripts)"
---

# Work Package Prompt: WP05 – Final Feature Lifecycle Commands

## ⚠️ CRITICAL SCOPE CORRECTION

**This prompt was rewritten on 2025-12-18** after discovering the original scope incorrectly targeted `.github/workflows/scripts/` (meta-scripts for spec-kitty deployment) instead of package scripts.

**Original incorrect scope**: Migrate release packaging meta-scripts
**Corrected scope**: Migrate final feature lifecycle bash wrappers (accept, merge)

---

## Objectives & Success Criteria

**Goal**: Complete the feature lifecycle command migration by exposing the existing `tasks_cli.py accept` and `merge` commands through the `spec-kitty agent feature` namespace, eliminating the last bash wrapper scripts.

**Success Criteria**:
- `spec-kitty agent feature accept --json` executes acceptance workflow with parseable JSON output
- `spec-kitty agent feature merge --json` executes merge workflow with parseable JSON output
- Auto-retry logic from `merge-feature.sh` preserved (auto-navigate to latest worktree if in wrong location)
- All commands work identically from main repo and worktree
- 90%+ test coverage for new feature commands
- Bash scripts replaced: `accept-feature.sh`, `merge-feature.sh`

**Why This Matters**: Accept and merge are the final steps in the feature lifecycle. Completing this work package means the entire spec-kitty workflow (specify → plan → tasks → implement → review → accept → merge) is available through the Python CLI.

---

## Context & Constraints

**Prerequisites**:
- **WP01 complete** ✅ (foundation infrastructure)
- **WP02 complete** ✅ (feature management with create-feature, check-prerequisites, setup-plan)
- Bash scripts to replace:
  - `scripts/bash/accept-feature.sh` - Thin wrapper calling `tasks_cli.py accept`
  - `scripts/bash/merge-feature.sh` - Thin wrapper calling `tasks_cli.py merge` with auto-retry logic

**Key Discovery**: The bash scripts are thin wrappers around existing Python code in `scripts/tasks/tasks_cli.py`. The `accept` and `merge` commands are already fully implemented in Python! This work package just needs to expose them through the agent namespace.

**Stream Assignment**: **Stream D (Agent Delta)** - Can run in parallel with WP03, WP04 after WP01-WP02 complete

**Files Owned by This Stream**:
- `src/specify_cli/cli/commands/agent/feature.py` ✅ (add accept/merge commands)
- `tests/unit/agent/test_feature.py` ✅ (add tests for new commands)

**Existing Implementation to Leverage**:
- `scripts/tasks/tasks_cli.py` - Contains `accept` and `merge` subcommands already implemented
- `scripts/bash/common.sh` - Contains `find_latest_feature_worktree()` utility for auto-retry

---

## Subtasks & Detailed Guidance

### T070 – Analyze existing accept and merge implementations

**Steps**:
1. Read `scripts/tasks/tasks_cli.py` to understand the `accept` and `merge` subcommands:
   ```bash
   python3 scripts/tasks/tasks_cli.py accept --help
   python3 scripts/tasks/tasks_cli.py merge --help
   ```

2. Read `scripts/bash/merge-feature.sh` to understand auto-retry logic (lines 10-30):
   - Checks if current branch matches feature pattern (`^[0-9]{3}-`)
   - If not, finds latest feature worktree using `find_latest_feature_worktree()`
   - Auto-runs command inside that worktree

3. Read `scripts/bash/common.sh` to find the `find_latest_feature_worktree()` function

**Acceptance**: Understanding documented in implementation notes

---

### T071 – Implement accept command in feature.py

**Goal**: Expose `tasks_cli.py accept` as `spec-kitty agent feature accept`

**Implementation**:

Add to `src/specify_cli/cli/commands/agent/feature.py`:

```python
@app.command(name="accept")
def accept_feature(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
) -> None:
    """Perform feature acceptance workflow.

    This command:
    1. Validates all tasks are in 'done' lane
    2. Runs acceptance checks from checklist files
    3. Creates acceptance report
    4. Marks feature as ready for merge

    Examples:
        # Run acceptance workflow
        spec-kitty agent feature accept

        # With JSON output for agents
        spec-kitty agent feature accept --json
    """
    try:
        # Import and call existing tasks_cli accept implementation
        from specify_cli.tasks_support import run_accept_workflow

        repo_root = locate_project_root()
        cwd = Path.cwd()

        # Detect feature directory
        feature_dir = _find_feature_directory(repo_root, cwd)
        feature_slug = feature_dir.name

        # Run acceptance workflow
        result = run_accept_workflow(
            repo_root=repo_root,
            feature_slug=feature_slug,
            json_mode=json_output
        )

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                console.print(f"[green]✓[/green] Feature {feature_slug} accepted")
            else:
                console.print(f"[red]✗[/red] Acceptance failed: {result.get('error')}")
                sys.exit(1)

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
```

**Alternative if tasks_support.py doesn't have clean functions**: Call `tasks_cli.py` as subprocess with proper argument passing.

**Acceptance**: Command runs and delegates to existing Python implementation

---

### T072 – Implement merge command with auto-retry logic

**Goal**: Expose `tasks_cli.py merge` as `spec-kitty agent feature merge` with auto-retry

**Implementation**:

Add to `src/specify_cli/cli/commands/agent/feature.py`:

```python
def _find_latest_feature_worktree(repo_root: Path) -> Optional[Path]:
    """Find the latest feature worktree by number.

    Migrated from find_latest_feature_worktree() in common.sh
    """
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return None

    latest_num = 0
    latest_worktree = None

    for worktree_dir in worktrees_dir.iterdir():
        if not worktree_dir.is_dir():
            continue

        # Match pattern: 001-feature-name
        match = re.match(r"^(\d{3})-", worktree_dir.name)
        if match:
            num = int(match.group(1))
            if num > latest_num:
                latest_num = num
                latest_worktree = worktree_dir

    return latest_worktree


@app.command(name="merge")
def merge_feature(
    target: Annotated[
        Optional[str],
        typer.Option(
            "--target",
            help="Target branch to merge into (defaults to 'main')"
        )
    ] = "main",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON for agent parsing"
        )
    ] = False,
    auto_retry: Annotated[
        bool,
        typer.Option(
            "--auto-retry/--no-auto-retry",
            help="Auto-navigate to latest worktree if in wrong location"
        )
    ] = True,
) -> None:
    """Merge feature branch into target branch.

    This command:
    1. Validates feature is accepted
    2. Merges feature branch into target (usually 'main')
    3. Cleans up worktree
    4. Deletes feature branch

    Auto-retry logic (from merge-feature.sh):
    If current branch doesn't match feature pattern (XXX-name),
    automatically finds and navigates to latest worktree.

    Examples:
        # Merge into main branch
        spec-kitty agent feature merge

        # Merge into specific branch with JSON output
        spec-kitty agent feature merge --target develop --json
    """
    try:
        repo_root = locate_project_root()
        cwd = Path.cwd()

        # Check if we're on a feature branch
        current_branch = get_current_branch(repo_root)
        is_feature_branch = re.match(r"^\d{3}-", current_branch)

        # Auto-retry logic: if not on feature branch, find latest worktree
        if not is_feature_branch and auto_retry:
            latest_worktree = _find_latest_feature_worktree(repo_root)
            if latest_worktree:
                if not json_output:
                    console.print(
                        f"[yellow]Auto-retry:[/yellow] Not on feature branch. "
                        f"Running merge in {latest_worktree}"
                    )

                # Re-run command in worktree
                result = subprocess.run(
                    ["spec-kitty", "agent", "feature", "merge", "--target", target, "--no-auto-retry"]
                    + (["--json"] if json_output else []),
                    cwd=latest_worktree,
                    capture_output=True,
                    text=True
                )

                if json_output:
                    print(result.stdout)
                else:
                    print(result.stdout)
                    if result.stderr:
                        print(result.stderr, file=sys.stderr)

                sys.exit(result.returncode)

        # Import and call existing tasks_cli merge implementation
        from specify_cli.tasks_support import run_merge_workflow

        feature_dir = _find_feature_directory(repo_root, cwd)
        feature_slug = feature_dir.name

        result = run_merge_workflow(
            repo_root=repo_root,
            feature_slug=feature_slug,
            target_branch=target,
            json_mode=json_output
        )

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                console.print(f"[green]✓[/green] Feature {feature_slug} merged into {target}")
            else:
                console.print(f"[red]✗[/red] Merge failed: {result.get('error')}")
                sys.exit(1)

    except Exception as e:
        if json_output:
            print(json.dumps({"error": str(e), "success": False}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
```

**Helper function** (add to feature.py or paths.py):

```python
def get_current_branch(repo_root: Path) -> str:
    """Get current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "main"
```

**Acceptance**: Merge command works with auto-retry logic

---

### T073 – Unit tests for accept and merge commands

Create tests in `tests/unit/agent/test_feature.py`:

```python
def test_accept_feature_json_output(mock_repo_with_feature):
    """Test accept command with JSON output."""
    # Mock tasks_cli accept workflow
    with patch("specify_cli.tasks_support.run_accept_workflow") as mock_accept:
        mock_accept.return_value = {"success": True, "feature": "001-test"}

        result = runner.invoke(app, ["accept", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True


def test_merge_feature_auto_retry(mock_repo_with_worktrees):
    """Test merge command auto-retry logic."""
    # When run from main repo (not feature branch)
    # Should auto-detect latest worktree and retry there
    with patch("specify_cli.cli.commands.agent.feature._find_latest_feature_worktree") as mock_find:
        mock_find.return_value = Path("/path/to/003-latest")

        # Run from main repo
        result = runner.invoke(app, ["merge", "--json"])

        # Should have attempted auto-retry
        mock_find.assert_called_once()


def test_find_latest_feature_worktree(tmp_path):
    """Test finding latest worktree by number."""
    worktrees = tmp_path / ".worktrees"
    worktrees.mkdir()

    (worktrees / "001-first").mkdir()
    (worktrees / "003-latest").mkdir()
    (worktrees / "002-middle").mkdir()
    (worktrees / "not-a-feature").mkdir()  # Should be ignored

    latest = _find_latest_feature_worktree(tmp_path)
    assert latest == worktrees / "003-latest"
```

**Acceptance**: Tests cover accept, merge, and auto-retry logic

---

### T074 – Integration test: Full feature lifecycle

Create integration test verifying the complete workflow:

```python
def test_full_feature_lifecycle(tmp_repo):
    """Test complete feature lifecycle: create → accept → merge."""

    # 1. Create feature
    result = run_cmd(["create-feature", "test-feature", "--json"])
    assert result["success"] is True
    feature_slug = result["feature_slug"]

    # 2. Simulate completing all tasks (move to done)
    worktree = tmp_repo / ".worktrees" / feature_slug
    # ... mark tasks as done ...

    # 3. Run acceptance
    result = run_cmd_in_dir(worktree, ["accept", "--json"])
    assert result["success"] is True

    # 4. Run merge
    result = run_cmd_in_dir(worktree, ["merge", "--target", "main", "--json"])
    assert result["success"] is True

    # 5. Verify cleanup
    assert not worktree.exists()  # Worktree should be deleted
    # Verify feature branch merged into main
```

**Acceptance**: Full lifecycle test passes

---

### T075 – Verify 90%+ test coverage

Run coverage analysis:

```bash
pytest tests/unit/agent/test_feature.py \
  --cov=src/specify_cli/cli/commands/agent/feature \
  --cov-report=term-missing
```

Add tests for uncovered branches until 90%+ achieved.

**Acceptance**: Coverage ≥ 90%

---

## Definition of Done Checklist

- [ ] Accept command implemented (T071)
- [ ] Merge command with auto-retry implemented (T072)
- [ ] Unit tests passing (T073)
- [ ] Integration test for full lifecycle passing (T074)
- [ ] 90%+ coverage achieved (T075)
- [ ] Bash wrapper scripts can be deleted in WP06

---

## Notes on Implementation Approach

**Leveraging Existing Code**: The bash scripts (`accept-feature.sh`, `merge-feature.sh`) are thin wrappers around `scripts/tasks/tasks_cli.py`. The actual business logic is already in Python.

**Two Options for Implementation**:

1. **Option A (Recommended)**: Import and call functions from `tasks_cli.py` or `tasks_support.py`
   - Cleaner integration
   - Easier to maintain
   - May require refactoring tasks_support.py to expose clean API

2. **Option B (Fallback)**: Call `tasks_cli.py` as subprocess
   - Quick implementation
   - Less coupling
   - Requires proper argument marshaling

**Choose Option A if possible**, falling back to Option B if tasks_support.py isn't structured for import.

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-18T01:30:00Z – claude – lane=planned – Prompt rewritten with corrected scope after discovering original targeted meta-scripts instead of package scripts
- 2025-12-18T00:07:10Z – claude – shell_pid=200 – lane=doing – Started implementation of accept/merge commands
