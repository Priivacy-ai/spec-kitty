---
work_package_id: WP05
title: Implement Command (NEW)
lane: done
history:
- timestamp: '2026-01-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: team
assignee: team
dependencies: [WP01, WP03]
phase: Phase 1 - Core Implementation
review_status: ''
reviewed_by: ''
shell_pid: manual
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T037
- T038
- T039
- T040
---

# Work Package Prompt: WP05 – Implement Command (NEW)

**Implementation command:**

```bash
spec-kitty implement WP05 --base WP03
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if needed.]*

---

## Objectives & Success Criteria

**Primary Goal**: Create new `spec-kitty implement WP##` command that creates workspace-per-WP on-demand, with `--base` flag for dependency-aware branching.

**Success Criteria**:

- ✅ New command `spec-kitty implement WP01` creates `.worktrees/###-feature-WP01/` workspace
- ✅ Command branches from main for WPs with no dependencies
- ✅ Command accepts `--base WPXX` flag and branches from specified WP's branch
- ✅ Validation prevents creating workspace if base doesn't exist
- ✅ Validation suggests --base flag if WP has dependencies but flag omitted
- ✅ Command registered in CLI router and accessible
- ✅ Unit tests pass

---

## Context & Constraints

**Why this command**: The implement command is the entry point for workspace creation in the workspace-per-WP model. It replaces the worktree creation that previously happened during `/spec-kitty.specify`.

**Reference Documents**:

- [plan.md](../plan.md) - Section 1.2: Command Design (implement WP## [--base WPXX])
- [spec.md](../spec.md) - User Story 2 (Dependency-Aware Workspace Creation), FR-004 through FR-008
- [data-model.md](../data-model.md) - Worktree entity definition

**Command Signature**:

```python
def implement(
    wp_id: str = typer.Argument(..., help="Work package ID (e.g., WP01)"),
    base: str = typer.Option(None, "--base", help="Base WP to branch from (e.g., WP01)"),
) -> None:
    """Create workspace for work package implementation."""
```

**Git Commands**:

```bash
# No dependencies (branch from main)
git worktree add .worktrees/010-feature-WP01 -b 010-feature-WP01

# With dependencies (branch from WP01)
git worktree add .worktrees/010-feature-WP02 -b 010-feature-WP02 010-feature-WP01
```

---

## Subtasks & Detailed Guidance

### Subtask T031 – Create implement.py module

**Purpose**: Create new CLI command file for the implement command.

**Steps**:

1. Create `src/specify_cli/cli/commands/implement.py`
2. Add standard imports:

   ```python
   from __future__ import annotations
   import subprocess
   from pathlib import Path
   import typer
   from rich.console import Console
   from specify_cli.cli import StepTracker
   from specify_cli.core.dependency_graph import (
       parse_wp_dependencies,
       get_dependents
   )
   from specify_cli.tasks_support import find_repo_root
   ```

3. Define `implement()` function with typer decorators
4. Add to CLI router (will be done in T039)

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (foundation for T032-T038)

---

### Subtask T032 – Implement workspace creation logic

**Purpose**: Core logic to create git worktree for WP workspace with proper branching.

**Steps**:

1. In `implement()` function, determine workspace path and branch name:

   ```python
   # Parse feature number from current directory or git branch
   feature_number, feature_slug = detect_feature_context()

   workspace_name = f"{feature_slug}-{wp_id}"
   workspace_path = repo_root / ".worktrees" / workspace_name
   branch_name = workspace_name  # Same as workspace dir name
   ```

2. Create worktree with correct base:

   ```python
   if base is None:
       # Branch from main
       cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name]
   else:
       # Branch from base WP's branch
       base_branch = f"{feature_slug}-{base}"
       cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name, base_branch]

   subprocess.run(cmd, check=True, cwd=repo_root)
   ```

3. Handle workspace directory existence:

   ```python
   if workspace_path.exists():
       # Check if valid worktree
       result = subprocess.run(
           ["git", "rev-parse", "--git-dir"],
           cwd=workspace_path,
           capture_output=True
       )
       if result.returncode == 0:
           console.print(f"[cyan]Workspace already exists, reusing: {workspace_path}[/cyan]")
           return
       else:
           raise FileExistsError(f"Directory exists but is not a valid worktree: {workspace_path}")
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (core logic)

**Notes**: Use existing patterns from `src/specify_cli/core/git_ops.py` and `worktree.py` for consistency

---

### Subtask T033 – Add --base parameter with validation

**Purpose**: Implement --base flag validation to ensure base workspace exists before creating dependent workspace.

**Steps**:

1. Add `--base` parameter to implement function:

   ```python
   base: str = typer.Option(None, "--base", help="Base WP to branch from (e.g., WP01)")
   ```

2. Validate base workspace exists if --base provided:

   ```python
   if base:
       base_workspace = repo_root / ".worktrees" / f"{feature_slug}-{base}"
       if not base_workspace.exists():
           console.print(f"[red]Error:[/red] Base workspace {base} does not exist")
           console.print(f"Implement {base} first: spec-kitty implement {base}")
           raise typer.Exit(1)

       # Verify it's a valid worktree
       result = subprocess.run(
           ["git", "rev-parse", "--git-dir"],
           cwd=base_workspace,
           capture_output=True
       )
       if result.returncode != 0:
           console.print(f"[red]Error:[/red] {base_workspace} exists but is not a valid worktree")
           raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (part of core logic in T032)

**Error Messages**:

- Base missing: "Base workspace WP01 does not exist. Implement WP01 first"
- Base invalid: "Directory exists but is not a valid worktree"

---

### Subtask T034 – Parse WP frontmatter for dependency validation

**Purpose**: Read WP's dependencies from frontmatter, suggest --base flag if missing.

**Steps**:

1. Locate WP file in main repo: `kitty-specs/###-feature/tasks/WP##-*.md`
2. Parse frontmatter using dependency_graph.parse_wp_dependencies()
3. Check if WP has dependencies but --base not provided:

   ```python
   from specify_cli.core.dependency_graph import parse_wp_dependencies

   # Find WP file
   wp_file = find_wp_file(repo_root, feature_slug, wp_id)
   declared_deps = parse_wp_dependencies(wp_file)

   if declared_deps and base is None:
       console.print(f"[red]Error:[/red] {wp_id} has dependencies: {declared_deps}")
       console.print(f"Use: spec-kitty implement {wp_id} --base {declared_deps[0]}")
       raise typer.Exit(1)
   ```

4. If --base provided, validate it matches declared dependencies:

   ```python
   if base and base not in declared_deps:
       console.print(f"[yellow]Warning:[/yellow] {wp_id} does not declare dependency on {base}")
       console.print(f"Declared dependencies: {declared_deps}")
       # Allow but warn (user might know better than parser)
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Helper Function**:

```python
def find_wp_file(repo_root: Path, feature_slug: str, wp_id: str) -> Path:
    """Find WP file in kitty-specs/###-feature/tasks/ directory."""
    tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    # Search for WP##-*.md pattern
    wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
    if not wp_files:
        raise FileNotFoundError(f"WP file not found for {wp_id}")
    return wp_files[0]
```

**Parallel?**: No (validation step in main workflow)

---

### Subtask T035 – Detect feature context from current directory

**Purpose**: Automatically determine feature number and slug from current working directory or git branch.

**Steps**:

1. Implement feature context detection:

   ```python
   def detect_feature_context() -> tuple[str, str]:
       """Detect feature number and slug from current context.

       Returns: (feature_number, feature_slug)
       Example: ("010", "010-workspace-per-wp")
       """
       # Method 1: From git branch
       result = subprocess.run(
           ["git", "rev-parse", "--abbrev-ref", "HEAD"],
           capture_output=True,
           text=True
       )
       branch = result.stdout.strip()

       # Check if branch matches feature pattern: ###-feature-name
       import re
       match = re.match(r'^(\d{3})-(.+)$', branch)
       if match:
           number = match.group(1)
           slug = branch
           return number, slug

       # Method 2: From current directory (if in kitty-specs/###-feature/)
       cwd = Path.cwd()
       if "kitty-specs" in cwd.parts:
           # Extract from path
           ...

       # Method 3: Error if can't detect
       raise RuntimeError("Cannot detect feature context. Are you in a feature branch?")
   ```

2. Call this function early in implement() to get feature context
3. Use feature_slug for workspace naming

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (utility function)

**Edge Cases**:

- Running from main branch → error (no feature context)
- Running from non-feature branch → error
- Running from WP workspace (010-feature-WP01 branch) → extract feature slug (010-feature)

---

### Subtask T036 – Create workspace naming convention

**Purpose**: Establish consistent naming for WP workspaces and branches.

**Steps**:

1. Workspace directory naming: `.worktrees/{feature_slug}-{wp_id}/`
   - Example: `.worktrees/010-workspace-per-wp-WP01/`
2. Branch naming: `{feature_slug}-{wp_id}`
   - Example: `010-workspace-per-wp-WP01`
3. Ensure consistent across all workspace operations

**Files**: `src/specify_cli/cli/commands/implement.py`

**Implementation**:

```python
# In implement() function
feature_number, feature_slug = detect_feature_context()

workspace_name = f"{feature_slug}-{wp_id}"  # e.g., "010-workspace-per-wp-WP01"
workspace_path = repo_root / ".worktrees" / workspace_name
branch_name = workspace_name  # Branch and directory have same name
```

**Parallel?**: No (part of T032 logic)

**Validation**: Ensure no name collisions (workspace name must be unique within .worktrees/)

---

### Subtask T037 – Implement branching logic (main vs base WP)

**Purpose**: Create correct git worktree command based on whether WP has dependencies.

**Steps**:

1. Determine base branch:

   ```python
   if base is None:
       # No dependencies - branch from main
       base_branch = "main"
       cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name]
   else:
       # Has dependencies - branch from base WP's branch
       base_branch = f"{feature_slug}-{base}"

       # Validate base branch exists in git
       result = subprocess.run(
           ["git", "rev-parse", "--verify", base_branch],
           capture_output=True
       )
       if result.returncode != 0:
           console.print(f"[red]Error:[/red] Base branch {base_branch} does not exist")
           raise typer.Exit(1)

       cmd = ["git", "worktree", "add", str(workspace_path), "-b", branch_name, base_branch]
   ```

2. Execute git command:

   ```python
   try:
       subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True)
   except subprocess.CalledProcessError as e:
       console.print(f"[red]Error:[/red] Git worktree creation failed")
       console.print(f"Command: {' '.join(cmd)}")
       console.print(f"Error: {e.stderr.decode()}")
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (core branching logic)

**Notes**: The third parameter in `git worktree add` is the base branch. When provided, new branch is created from that base instead of current HEAD.

---

### Subtask T038 – Add StepTracker progress display

**Purpose**: Provide user feedback during workspace creation using Rich StepTracker.

**Steps**:

1. Import StepTracker: `from specify_cli.cli import StepTracker`
2. Create tracker with steps:

   ```python
   tracker = StepTracker(f"Implement {wp_id}")
   tracker.add("detect", "Detect feature context")
   tracker.add("validate", "Validate dependencies")
   tracker.add("create", "Create workspace")
   tracker.add("setup", "Setup workspace directory")
   ```

3. Update tracker at each stage:

   ```python
   tracker.start("detect")
   feature_number, feature_slug = detect_feature_context()
   tracker.complete("detect", f"Feature: {feature_slug}")

   tracker.start("validate")
   # ... validation logic
   tracker.complete("validate", f"Base: {base or 'main'}")

   tracker.start("create")
   # ... git worktree add
   tracker.complete("create", f"Workspace: {workspace_path}")

   console.print(tracker.render())
   ```

4. Handle errors with tracker.error():

   ```python
   except Exception as e:
       tracker.error("create", str(e))
       console.print(tracker.render())
       raise
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (integrated throughout command)

**Example Output**:

```
Implement WP01
  ✓ Detect feature context → Feature: 010-workspace-per-wp
  ✓ Validate dependencies → Base: main
  ✓ Create workspace → Workspace: .worktrees/010-workspace-per-wp-WP01
  ✓ Setup workspace directory → Ready

✓ Workspace created successfully
```

---

### Subtask T039 – Register implement command in CLI router

**Purpose**: Make `spec-kitty implement` command available in CLI.

**Steps**:

1. Locate CLI app registration (likely in `src/specify_cli/cli/app.py` or `src/specify_cli/cli/__init__.py`)
2. Import implement command: `from specify_cli.cli.commands.implement import implement`
3. Register with typer app:

   ```python
   app.command(name="implement", help="Create workspace for work package implementation")(implement)
   ```

4. Verify command shows in help: `spec-kitty --help` should list implement
5. Test command is accessible: `spec-kitty implement --help`

**Files**:

- `src/specify_cli/cli/commands/implement.py` (command definition)
- `src/specify_cli/cli/app.py` or similar (command registration)

**Parallel?**: No (final integration step)

**Validation**:

```bash
spec-kitty implement --help
# Should display:
# Usage: spec-kitty implement WP_ID [OPTIONS]
#
# Create workspace for work package implementation.
#
# Arguments:
#   WP_ID  Work package ID (e.g., WP01)
#
# Options:
#   --base TEXT  Base WP to branch from (e.g., WP01)
```

---

### Subtask T040 – Write unit tests for implement command

**Purpose**: Test implement command logic with mocked git operations.

**Steps**:

1. Create `tests/specify_cli/test_implement_command.py`
2. Mock git subprocess calls to avoid creating actual worktrees
3. Test cases:
   - Implement WP01 (no deps) → calls git worktree add from main
   - Implement WP02 --base WP01 → calls git worktree add from WP01 branch
   - Implement WP02 --base WP01 (WP01 doesn't exist) → error
   - Implement WP02 (has deps, no --base) → error with suggestion
   - Feature context detection from various locations
   - Workspace naming correctness

**Files**: `tests/specify_cli/test_implement_command.py`

**Example Test**:

```python
from unittest.mock import patch, MagicMock

def test_implement_no_dependencies(tmp_path, monkeypatch):
    """Test implement WP01 creates workspace from main."""
    # Setup
    monkeypatch.chdir(tmp_path)
    # Mock git commands
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"010-feature")

        # Run implement WP01
        implement("WP01", base=None)

        # Verify git worktree add called correctly
        calls = mock_run.call_args_list
        worktree_call = [c for c in calls if "worktree" in str(c)]
        assert len(worktree_call) > 0
        # Verify command: git worktree add .worktrees/010-feature-WP01 -b 010-feature-WP01
```

**Parallel?**: Can be written in parallel with implementation (but runs after)

---

## Additional Implementation Details

### Feature Context Detection

**detect_feature_context() implementation:**

```python
def detect_feature_context() -> tuple[str, str]:
    """Detect feature number and slug from current context."""
    # Try git branch first
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0:
        branch = result.stdout.strip()

        # Pattern 1: Feature branch (###-feature-name)
        match = re.match(r'^(\d{3})-(.+)$', branch)
        if match:
            number = match.group(1)
            slug = branch
            return number, slug

        # Pattern 2: WP branch (###-feature-name-WP##)
        # Extract feature slug by removing -WP## suffix
        match = re.match(r'^((\d{3})-.+)-WP\d{2}$', branch)
        if match:
            slug = match.group(1)
            number = match.group(2)
            return number, slug

    # Try current directory
    cwd = Path.cwd()
    # Look for kitty-specs/###-feature-name/ in path
    for part in cwd.parts:
        match = re.match(r'^(\d{3})-(.+)$', part)
        if match:
            number = match.group(1)
            slug = part
            return number, slug

    # Cannot detect
    console.print("[red]Error:[/red] Cannot detect feature context")
    console.print("Run this command from a feature branch or feature directory")
    raise typer.Exit(1)
```

### Workspace Path Validation

**Ensure workspace path doesn't conflict:**

```python
def validate_workspace_path(workspace_path: Path, wp_id: str):
    """Ensure workspace path is available or reusable."""
    if not workspace_path.exists():
        return  # Good - doesn't exist

    # Check if it's a valid git worktree
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=workspace_path,
        capture_output=True,
        check=False
    )

    if result.returncode == 0:
        # Valid worktree exists
        console.print(f"[cyan]Workspace for {wp_id} already exists[/cyan]")
        console.print(f"Reusing: {workspace_path}")
        return  # Reuse existing

    # Directory exists but not a worktree
    console.print(f"[red]Error:[/red] Directory exists but is not a valid worktree")
    console.print(f"Path: {workspace_path}")
    console.print(f"Remove manually: rm -rf {workspace_path}")
    raise typer.Exit(1)
```

---

## Test Strategy

**Unit Tests**: `tests/specify_cli/test_implement_command.py`

**Test Coverage**:

- Feature context detection (various branches, directories)
- Workspace creation (no deps, with deps)
- Validation (base exists, dependencies match, errors)
- StepTracker integration
- Error paths (missing base, invalid WP ID, etc.)

**Execution**:

```bash
pytest tests/specify_cli/test_implement_command.py -v
```

**Mocking Strategy**: Mock subprocess.run to avoid creating real worktrees during tests. Use tmp_path fixture for filesystem operations.

---

## Risks & Mitigations

**Risk 1: Feature context detection fails in edge cases**

- Impact: Command can't determine which feature to create workspace for
- Mitigation: Support multiple detection methods (git branch, directory path), clear error if all fail

**Risk 2: Race condition when multiple agents run implement simultaneously**

- Impact: Two agents try to create same workspace, one fails
- Mitigation: Workspace existence check, reuse if valid worktree exists

**Risk 3: Git worktree add fails**

- Impact: Workspace creation fails mid-operation, leaves partial state
- Mitigation: Git worktree add is atomic, clear error messages with git stderr output

**Risk 4: Base branch doesn't exist in git**

- Impact: Trying to branch from WP01 branch that was never created
- Mitigation: Validate base branch exists in git before worktree creation

---

## Definition of Done Checklist

- [ ] implement.py module created (T031)
- [ ] Workspace creation logic implemented (T032)
- [ ] --base parameter validation implemented (T033)
- [ ] WP frontmatter dependency parsing implemented (T034)
- [ ] Feature context detection implemented (T035)
- [ ] Workspace naming convention established (T036)
- [ ] Branching logic handles both main and base WP (T037)
- [ ] StepTracker progress display added (T038)
- [ ] Command registered in CLI router (T039)
- [ ] Unit tests written and passing (T040)
- [ ] Manual test: Run implement WP01, verify workspace created
- [ ] Manual test: Run implement WP02 --base WP01, verify branching correct

---

## Review Guidance

**Reviewers should verify**:

1. **Command is user-friendly**: Clear error messages, helpful suggestions for missing --base
2. **Validation is robust**: All edge cases handled (missing base, invalid IDs, etc.)
3. **Git commands are correct**: Proper worktree add syntax with base branch parameter
4. **StepTracker output is clear**: Users understand what's happening at each step
5. **Tests are comprehensive**: Cover happy paths and error paths

**Key Acceptance Checkpoints**:

- Run `spec-kitty implement WP01` → workspace created from main
- Run `spec-kitty implement WP02 --base WP01` → workspace created from WP01 branch
- Run `spec-kitty implement WP02` (missing --base but has deps) → clear error with suggestion
- Run `spec-kitty implement WP02 --base WP99` (missing base) → clear error

**Manual Testing Commands**:

```bash
# Create test feature in main
cd /path/to/test-project
/spec-kitty.specify "Test Feature"
/spec-kitty.tasks

# Test implement
spec-kitty implement WP01
ls .worktrees/  # Should show: 011-test-feature-WP01/

# Test with dependencies
spec-kitty implement WP02 --base WP01
ls .worktrees/  # Should show: 011-test-feature-WP01/, 011-test-feature-WP02/

# Verify branching
cd .worktrees/011-test-feature-WP02
git log --oneline --graph --all  # Should show WP02 branched from WP01
```

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

Move this WP between lanes using:

```bash
spec-kitty agent workflow implement WP05
```

Or edit the `lane:` field in frontmatter directly.

- 2026-01-08T10:06:42Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T10:13:01Z – unknown – lane=for_review – Ready for review - all tests passing, command working correctly
- 2026-01-08T10:15:11Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T10:22:11Z – unknown – lane=done – Review passed - all requirements met
