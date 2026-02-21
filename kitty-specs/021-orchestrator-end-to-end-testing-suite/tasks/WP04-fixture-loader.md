---
work_package_id: "WP04"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "Fixture Loader"
phase: "Phase 0 - Foundation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "20551"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: ["WP03"]
history:
  - timestamp: "2026-01-19T09:30:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Fixture Loader

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP03 (needs dataclasses and validation functions).

---

## Objectives & Success Criteria

Implement fixture loading that restores checkpoints to usable test state:

- [ ] `copy_fixture_to_temp()` creates isolated copy in temp directory
- [ ] `init_git_repo()` initializes git with main branch and initial commit
- [ ] `create_worktrees_from_metadata()` recreates worktrees from JSON
- [ ] `load_checkpoint()` assembles complete TestContext
- [ ] `cleanup_test_context()` properly removes temp directories

## Context & Constraints

**Reference Documents**:

- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Loader behavior steps
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - TestContext

**Existing Code**:

- `src/specify_cli/orchestrator/testing/fixtures.py` - From WP03
- `src/specify_cli/core/vcs/git.py` - Git operations (if available)

**Constraints**:

- Use `tempfile.mkdtemp()` for isolation
- Git operations via subprocess (not GitPython)
- Cleanup must handle failures gracefully

---

## Subtasks & Detailed Guidance

### Subtask T015 – Implement copy_fixture_to_temp()

**Purpose**: Copy a checkpoint fixture to an isolated temp directory.

**Steps**:

1. Add to `fixtures.py`:

   ```python
   import shutil
   import tempfile
   from pathlib import Path

   def copy_fixture_to_temp(checkpoint: FixtureCheckpoint) -> Path:
       """Copy checkpoint fixture to a temporary directory.

       Args:
           checkpoint: The checkpoint to copy

       Returns:
           Path to the temporary directory

       Raises:
           FileNotFoundError: If checkpoint doesn't exist
       """
       if not checkpoint.exists():
           raise FileNotFoundError(
               f"Checkpoint not found or incomplete: {checkpoint.path}"
           )

       # Create temp directory
       temp_dir = Path(tempfile.mkdtemp(prefix=f"orchestrator_test_{checkpoint.name}_"))

       # Copy feature directory
       shutil.copytree(
           checkpoint.feature_dir,
           temp_dir / "kitty-specs" / "test-feature",
           dirs_exist_ok=True,
       )

       # Copy state file to feature dir
       shutil.copy2(
           checkpoint.state_file,
           temp_dir / "kitty-specs" / "test-feature" / ".orchestration-state.json",
       )

       # Copy worktrees.json for reference
       shutil.copy2(
           checkpoint.worktrees_file,
           temp_dir / "worktrees.json",
       )

       return temp_dir
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~40 lines)

**Parallel?**: Yes - can proceed with T016-T018

---

### Subtask T016 – Implement init_git_repo()

**Purpose**: Initialize a git repository in the temp directory.

**Steps**:

1. Add to `fixtures.py`:

   ```python
   import subprocess

   class GitError(Exception):
       """Error during git operations."""
       pass

   def init_git_repo(repo_path: Path) -> None:
       """Initialize a git repository with initial commit.

       Args:
           repo_path: Path to initialize as git repo

       Raises:
           GitError: If git commands fail
       """
       try:
           # Initialize repo
           subprocess.run(
               ["git", "init"],
               cwd=repo_path,
               check=True,
               capture_output=True,
           )

           # Configure git user for commits
           subprocess.run(
               ["git", "config", "user.email", "test@example.com"],
               cwd=repo_path,
               check=True,
               capture_output=True,
           )
           subprocess.run(
               ["git", "config", "user.name", "Test User"],
               cwd=repo_path,
               check=True,
               capture_output=True,
           )

           # Add all files
           subprocess.run(
               ["git", "add", "."],
               cwd=repo_path,
               check=True,
               capture_output=True,
           )

           # Initial commit
           subprocess.run(
               ["git", "commit", "-m", "Initial test fixture commit"],
               cwd=repo_path,
               check=True,
               capture_output=True,
           )

       except subprocess.CalledProcessError as e:
           raise GitError(
               f"Git command failed: {e.cmd}\n"
               f"stdout: {e.stdout.decode()}\n"
               f"stderr: {e.stderr.decode()}"
           )
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~55 lines)

**Parallel?**: Yes - can proceed with T015, T017, T018

---

### Subtask T017 – Implement create_worktrees_from_metadata()

**Purpose**: Recreate git worktrees from the saved metadata.

**Steps**:

1. Add to `fixtures.py`:

   ```python
   def create_worktrees_from_metadata(
       repo_path: Path,
       worktrees: list[WorktreeMetadata]
   ) -> None:
       """Create git worktrees from metadata.

       Args:
           repo_path: Path to the git repository
           worktrees: List of worktree metadata

       Raises:
           GitError: If worktree creation fails
       """
       for wt in worktrees:
           worktree_path = repo_path / wt.relative_path

           # Ensure parent directory exists
           worktree_path.parent.mkdir(parents=True, exist_ok=True)

           try:
               # Create branch if it doesn't exist
               subprocess.run(
                   ["git", "branch", wt.branch_name],
                   cwd=repo_path,
                   check=False,  # Branch may already exist
                   capture_output=True,
               )

               # Create worktree
               cmd = ["git", "worktree", "add", str(worktree_path), wt.branch_name]
               subprocess.run(
                   cmd,
                   cwd=repo_path,
                   check=True,
                   capture_output=True,
               )

               # Checkout specific commit if specified
               if wt.commit_hash:
                   subprocess.run(
                       ["git", "checkout", wt.commit_hash],
                       cwd=worktree_path,
                       check=True,
                       capture_output=True,
                   )

           except subprocess.CalledProcessError as e:
               raise GitError(
                   f"Failed to create worktree {wt.wp_id}: {e.cmd}\n"
                   f"stdout: {e.stdout.decode()}\n"
                   f"stderr: {e.stderr.decode()}"
               )
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~50 lines)

**Parallel?**: Yes - can proceed with T015, T016, T018

---

### Subtask T018 – Implement load_orchestration_state()

**Purpose**: Load and deserialize the OrchestrationRun from state file.

**Steps**:

1. This is already implemented in T014 as `load_state_file()`. This subtask ensures it's properly integrated:

   ```python
   def load_orchestration_state(feature_dir: Path) -> OrchestrationRun:
       """Load orchestration state from feature directory.

       Args:
           feature_dir: Path to feature directory containing state file

       Returns:
           Loaded OrchestrationRun

       Raises:
           StateFileError: If state file is invalid or missing
       """
       state_path = feature_dir / ".orchestration-state.json"
       return load_state_file(state_path)
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~15 lines)

**Parallel?**: Yes - can proceed with T015-T017

---

### Subtask T019 – Implement load_checkpoint() - assemble TestContext

**Purpose**: Main entry point that loads a checkpoint and returns complete TestContext.

**Steps**:

1. Add main loader function:

   ```python
   from specify_cli.orchestrator.testing.paths import TestPath, select_test_path_sync

   def load_checkpoint(
       checkpoint: FixtureCheckpoint,
       test_path: TestPath | None = None,
   ) -> TestContext:
       """Load a checkpoint fixture into a usable test context.

       Args:
           checkpoint: The checkpoint to load
           test_path: Optional pre-selected test path (auto-detected if None)

       Returns:
           Complete TestContext ready for testing

       Raises:
           FileNotFoundError: If checkpoint doesn't exist
           GitError: If git operations fail
           StateFileError: If state file is invalid
       """
       # Copy fixture to temp
       temp_dir = copy_fixture_to_temp(checkpoint)
       repo_root = temp_dir
       feature_dir = temp_dir / "kitty-specs" / "test-feature"

       try:
           # Initialize git repo
           init_git_repo(repo_root)

           # Load worktrees metadata
           worktrees_path = temp_dir / "worktrees.json"
           worktrees = load_worktrees_file(worktrees_path)

           # Create worktrees
           if worktrees:
               create_worktrees_from_metadata(repo_root, worktrees)

           # Load orchestration state
           state = load_orchestration_state(feature_dir)

           # Get or detect test path
           if test_path is None:
               test_path = select_test_path_sync()

           return TestContext(
               temp_dir=temp_dir,
               repo_root=repo_root,
               feature_dir=feature_dir,
               test_path=test_path,
               checkpoint=checkpoint,
               orchestration_state=state,
               worktrees=worktrees,
           )

       except Exception:
           # Cleanup on failure
           cleanup_temp_dir(temp_dir)
           raise
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~55 lines)

**Parallel?**: No - depends on T015-T018

---

### Subtask T020 – Implement cleanup_test_context()

**Purpose**: Properly clean up test context including worktrees.

**Steps**:

1. Add cleanup functions:

   ```python
   import atexit
   from typing import Set

   # Track temp directories for cleanup
   _temp_dirs_to_cleanup: Set[Path] = set()

   def cleanup_temp_dir(temp_dir: Path) -> None:
       """Remove a temporary directory and its contents.

       Args:
           temp_dir: Path to remove
       """
       if temp_dir.exists():
           # Remove worktrees first (git requirement)
           worktrees_dir = temp_dir / ".worktrees"
           if worktrees_dir.exists():
               try:
                   subprocess.run(
                       ["git", "worktree", "prune"],
                       cwd=temp_dir,
                       check=False,
                       capture_output=True,
                   )
               except Exception:
                   pass  # Best effort

           # Remove directory tree
           shutil.rmtree(temp_dir, ignore_errors=True)

       _temp_dirs_to_cleanup.discard(temp_dir)

   def cleanup_test_context(ctx: TestContext) -> None:
       """Clean up a test context.

       Args:
           ctx: The test context to clean up
       """
       cleanup_temp_dir(ctx.temp_dir)

   def register_for_cleanup(temp_dir: Path) -> None:
       """Register a temp directory for cleanup at exit."""
       _temp_dirs_to_cleanup.add(temp_dir)

   def _cleanup_all_temp_dirs() -> None:
       """Cleanup handler for atexit."""
       for temp_dir in list(_temp_dirs_to_cleanup):
           cleanup_temp_dir(temp_dir)

   # Register cleanup handler
   atexit.register(_cleanup_all_temp_dirs)
   ```

2. Update `load_checkpoint` to register for cleanup:

   ```python
   # In load_checkpoint, after creating temp_dir:
   register_for_cleanup(temp_dir)
   ```

**Files**:

- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~50 lines)

**Parallel?**: No - should be last in sequence

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Temp directory not cleaned up | Use atexit handler and try/finally |
| Git worktree prune fails | Use ignore_errors for cleanup operations |
| Race condition with cleanup | Track dirs in module-level set |
| Circular import with paths.py | Import inside function if needed |

## Review Guidance

**Key Acceptance Checkpoints**:

- [ ] `load_checkpoint()` returns valid TestContext
- [ ] Git repo is properly initialized with commits
- [ ] Worktrees are created at correct paths
- [ ] State file is loaded into `orchestration_state`
- [ ] Cleanup removes all files including worktrees
- [ ] atexit handler catches forgotten cleanups

**Code Quality**:

- All git operations use subprocess with proper error handling
- Cleanup is idempotent (safe to call multiple times)
- No resource leaks (temp dirs always cleaned up)

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T09:59:01Z – claude – shell_pid=12835 – lane=doing – Started implementation via workflow command
- 2026-01-19T10:08:07Z – claude – shell_pid=12835 – lane=for_review – Ready for review: Implemented fixture loader functions (copy_fixture_to_temp, init_git_repo, create_worktrees_from_metadata, load_orchestration_state, load_checkpoint, cleanup functions). 60 tests passing.
- 2026-01-19T10:09:08Z – claude-opus – shell_pid=20551 – lane=doing – Started review via workflow command
- 2026-01-19T10:12:06Z – claude-opus – shell_pid=20551 – lane=done – Review passed: All 6 subtasks (T015-T020) implemented correctly. 60 tests passing. Code follows spec requirements - copy_fixture_to_temp with tempfile.mkdtemp, init_git_repo with subprocess, create_worktrees_from_metadata, load_orchestration_state, load_checkpoint assembling TestContext, and cleanup functions with atexit handler. Dependency WP03 is merged.
