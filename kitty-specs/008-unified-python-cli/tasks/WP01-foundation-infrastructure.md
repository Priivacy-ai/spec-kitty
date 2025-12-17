---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Foundation Infrastructure"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation Infrastructure

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Establish core agent CLI namespace and path resolution infrastructure for all parallel work streams.

**Success Criteria**:
- `spec-kitty agent --help` displays help text showing agent subcommands
- Path resolution works correctly from main repository
- Path resolution works correctly from worktree
- Broken symlink handling does not crash (graceful error)
- Test infrastructure created and pytest runs successfully
- All 4 stub modules (feature, tasks, context, release) import without errors

**Why This Matters**: Phase 1 is the PREREQUISITE for all parallel work (WP02-WP05). Foundation delays block everything. Focus on minimal stubs to unblock parallel streams - deep implementation happens in WP02-WP05.

---

## Context & Constraints

**Prerequisites**:
- Research phase complete (research.md validates approach) ✅
- Worktree exists: `.worktrees/008-unified-python-cli/`
- Python 3.11+ installed
- Typer already in project dependencies

**Related Documents**:
- Spec: `kitty-specs/008-unified-python-cli/spec.md` (FR-005, FR-007, FR-012, FR-013, FR-014)
- Plan: `kitty-specs/008-unified-python-cli/plan.md` (Phase 1 section)
- Research: `kitty-specs/008-unified-python-cli/research.md` (Path resolution validation)
- Quickstart: `kitty-specs/008-unified-python-cli/quickstart.md` (Development patterns)

**Architectural Decisions**:
- Use Typer sub-app pattern for agent namespace (decision from research.md)
- Three-tier path resolution: env var → git → `.kittify/` marker (research validation)
- Check `is_symlink()` before `exists()` for broken symlinks (existing pattern, commit d9a07fc)

**Constraints**:
- Must complete in 2 days maximum (blocks all parallel work)
- Stub modules only - no deep command implementation yet
- Must work identically in main repo and worktree
- Must support Windows (no symlink assumptions)

---

## Subtasks & Detailed Guidance

### T001 – Create agent command directory structure

**Purpose**: Establish `src/specify_cli/cli/commands/agent/` namespace for all agent commands.

**Steps**:
1. Navigate to repository root
2. Create directory: `mkdir -p src/specify_cli/cli/commands/agent`
3. Verify directory exists

**Files**: `src/specify_cli/cli/commands/agent/` (directory)

**Parallel?**: No (prerequisite for T002-T006)

**Notes**: This directory will contain 4 modules (feature, tasks, context, release) plus __init__.py.

---

### T002 – Create agent __init__.py with Typer sub-app registration

**Purpose**: Register agent namespace as Typer sub-app so `spec-kitty agent` works.

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/__init__.py`
2. Import Typer
3. Create Typer app instance:
   ```python
   import typer
   from typing_extensions import Annotated

   app = typer.Typer(
       name="agent",
       help="Commands for AI agents to execute spec-kitty workflows programmatically",
       no_args_is_help=True
   )
   ```
4. Import and register stub modules (will be created in T003-T006):
   ```python
   from . import feature, tasks, context, release

   app.add_typer(feature.app, name="feature")
   app.add_typer(tasks.app, name="tasks")
   app.add_typer(context.app, name="context")
   app.add_typer(release.app, name="release")
   ```

**Files**: `src/specify_cli/cli/commands/agent/__init__.py`

**Parallel?**: No (depends on T001, prerequisite for T007)

**Notes**: Follow Typer sub-app pattern from research.md (EV014). The `no_args_is_help=True` ensures `spec-kitty agent` shows help without needing `--help`.

---

### T003 – Create feature.py stub module

**Purpose**: Placeholder for feature lifecycle commands (implemented in WP02).

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/feature.py`
2. Create minimal Typer app:
   ```python
   import typer

   app = typer.Typer(
       name="feature",
       help="Feature lifecycle commands for AI agents",
       no_args_is_help=True
   )

   # Deep implementation in WP02
   ```

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Parallel?**: Yes (can run concurrently with T004-T006)

**Notes**: Stub only - no commands yet. WP02 (Stream A) will implement `create-feature`, `check-prerequisites`, `setup-plan`.

---

### T004 – Create tasks.py stub module

**Purpose**: Placeholder for task workflow commands (implemented in WP03).

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/tasks.py`
2. Create minimal Typer app:
   ```python
   import typer

   app = typer.Typer(
       name="tasks",
       help="Task workflow commands for AI agents",
       no_args_is_help=True
   )

   # Deep implementation in WP03
   ```

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Parallel?**: Yes (can run concurrently with T003, T005, T006)

**Notes**: Stub only - no commands yet. WP03 (Stream B) will implement `move-task`, `mark-status`, etc.

---

### T005 – Create context.py stub module

**Purpose**: Placeholder for agent context management commands (implemented in WP04).

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/context.py`
2. Create minimal Typer app:
   ```python
   import typer

   app = typer.Typer(
       name="context",
       help="Agent context management commands",
       no_args_is_help=True
   )

   # Deep implementation in WP04
   ```

**Files**: `src/specify_cli/cli/commands/agent/context.py`

**Parallel?**: Yes (can run concurrently with T003, T004, T006)

**Notes**: Stub only - no commands yet. WP04 (Stream C) will implement `update-context`.

---

### T006 – Create release.py stub module

**Purpose**: Placeholder for release packaging commands (implemented in WP05).

**Steps**:
1. Create `src/specify_cli/cli/commands/agent/release.py`
2. Create minimal Typer app:
   ```python
   import typer

   app = typer.Typer(
       name="release",
       help="Release packaging commands for AI agents",
       no_args_is_help=True
   )

   # Deep implementation in WP05
   ```

**Files**: `src/specify_cli/cli/commands/agent/release.py`

**Parallel?**: Yes (can run concurrently with T003, T004, T005)

**Notes**: Stub only - no commands yet. WP05 (Stream D) will implement `build-release`.

---

### T007 – Register agent sub-app in main CLI

**Purpose**: Make `spec-kitty agent` accessible by registering in main CLI entry point.

**Steps**:
1. Open `src/specify_cli/cli/__init__.py` (or main CLI file)
2. Import agent module:
   ```python
   from .commands import agent
   ```
3. Register agent sub-app with main Typer app:
   ```python
   app.add_typer(agent.app, name="agent")
   ```
4. Verify import chain works

**Files**: `src/specify_cli/cli/__init__.py`

**Parallel?**: No (depends on T002-T006)

**Notes**: Exact file may vary - find where main `app = typer.Typer()` is defined. Registration enables `spec-kitty agent --help`.

---

### T008 – Enhance paths.py with worktree detection logic

**Purpose**: Upgrade path resolution to automatically detect worktree vs main repo execution.

**Steps**:
1. Read existing `src/specify_cli/core/paths.py`
2. Review `locate_project_root()` function (exists from research SR001)
3. Enhance with three-tier resolution:
   - Tier 1: Check `SPECIFY_REPO_ROOT` env var (if set, return immediately)
   - Tier 2: Try `git rev-parse --show-toplevel` (use subprocess)
   - Tier 3: Walk up directory tree looking for `.kittify/` marker
4. Add worktree detection:
   ```python
   def is_worktree_context(current_path: Path) -> bool:
       """Detect if current path is within .worktrees/ directory"""
       return ".worktrees" in current_path.parts
   ```
5. Return tuple: `(repo_root: Path, is_worktree: bool)`

**Files**: `src/specify_cli/core/paths.py`

**Parallel?**: No (critical for all commands)

**Notes**: Research EV007 validates this approach. Git command: `subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)`.

---

### T009 – Add environment variable support SPECIFY_REPO_ROOT

**Purpose**: Allow override of path detection via env var (useful for CI/CD).

**Steps**:
1. In `paths.py`, check env var first in resolution hierarchy:
   ```python
   import os

   def locate_project_root():
       # Tier 1: Environment variable
       if env_root := os.getenv("SPECIFY_REPO_ROOT"):
           return Path(env_root)
       # Tier 2: Git...
       # Tier 3: Marker...
   ```
2. Validate env var path exists and has `.kittify/`
3. Document in docstring

**Files**: `src/specify_cli/core/paths.py`

**Parallel?**: No (part of T008 enhancement)

**Notes**: Walrus operator `:=` requires Python 3.8+ (we have 3.11+). This is the FIRST tier in resolution strategy.

---

### T010 – Ensure broken symlink handling

**Purpose**: Prevent crashes when symlinks are broken (worktree edge case).

**Steps**:
1. In `paths.py`, anywhere checking file/directory existence, use pattern:
   ```python
   if path.is_symlink() and not path.exists():
       # Broken symlink detected
       raise FileNotFoundError(f"Broken symlink detected: {path}")
   elif path.exists():
       # Valid path
       return path
   ```
2. Apply pattern consistently
3. Write helper function if needed

**Files**: `src/specify_cli/core/paths.py`

**Parallel?**: No (part of T008 enhancement)

**Notes**: This pattern comes from commit d9a07fc (research EV008). Check `is_symlink()` BEFORE `exists()` because broken symlinks return False for `exists()`.

---

### T011 – Create tests/unit/agent/ directory

**Purpose**: Establish test infrastructure for agent command unit tests.

**Steps**:
1. Create directory: `mkdir -p tests/unit/agent`
2. Create `tests/unit/agent/__init__.py` (empty, makes it a package)
3. Verify pytest discovers the directory

**Files**: `tests/unit/agent/` (directory + `__init__.py`)

**Parallel?**: Yes (can run concurrently with T012)

**Notes**: Unit tests in WP02-WP05 will create `test_feature.py`, `test_tasks.py`, etc. in this directory.

---

### T012 – Create tests/integration/ directory

**Purpose**: Establish test infrastructure for end-to-end agent workflow tests.

**Steps**:
1. Create directory: `mkdir -p tests/integration`
2. Create `tests/integration/__init__.py` (empty)
3. Verify pytest discovers the directory

**Files**: `tests/integration/` (directory + `__init__.py`)

**Parallel?**: Yes (can run concurrently with T011)

**Notes**: Integration tests in WP02-WP05 and WP07 will create workflow tests in this directory.

---

### T013 – Create pytest fixtures for worktree testing

**Purpose**: Provide test utilities for simulating worktree environments.

**Steps**:
1. Open or create `tests/conftest.py` (pytest fixture file)
2. Add worktree fixture:
   ```python
   import pytest
   from pathlib import Path
   import tempfile

   @pytest.fixture
   def mock_worktree(tmp_path):
       """Create temporary worktree structure for testing"""
       worktree = tmp_path / ".worktrees" / "test-feature"
       worktree.mkdir(parents=True)

       # Create .kittify marker
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       # Create feature directory
       feature_dir = worktree / "kitty-specs" / "001-test-feature"
       feature_dir.mkdir(parents=True)

       return {
           "repo_root": tmp_path,
           "worktree_path": worktree,
           "feature_dir": feature_dir
       }
   ```
3. Add main repo fixture:
   ```python
   @pytest.fixture
   def mock_main_repo(tmp_path):
       """Create temporary main repository structure"""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       specs = tmp_path / "kitty-specs"
       specs.mkdir()

       return tmp_path
   ```

**Files**: `tests/conftest.py`

**Parallel?**: No (depends on T011, T012)

**Notes**: These fixtures enable testing path resolution from both contexts. WP02-WP05 will use them extensively.

---

### T014 – Verify spec-kitty agent --help works

**Purpose**: Manual smoke test that foundation infrastructure is wired correctly.

**Steps**:
1. Install package in development mode: `pip install -e .` (from repo root)
2. Run: `spec-kitty agent --help`
3. Verify output shows:
   - "Commands for AI agents to execute spec-kitty workflows programmatically"
   - Subcommands: feature, tasks, context, release
4. Run: `spec-kitty agent feature --help` (should show feature help, even if empty)
5. Verify no import errors or crashes

**Files**: N/A (manual test)

**Parallel?**: No (depends on T001-T007)

**Notes**: This is the acceptance gate for Phase 1. If this fails, parallel streams cannot begin. Troubleshoot import errors by running `python -c "from specify_cli.cli.commands import agent"`.

---

### T015 – Unit test: Path resolution from main repo

**Purpose**: Verify path resolution works correctly from main repository.

**Steps**:
1. Create `tests/unit/test_paths.py`
2. Test `locate_project_root()` with `mock_main_repo` fixture:
   ```python
   from specify_cli.core.paths import locate_project_root

   def test_locate_project_root_from_main(mock_main_repo, monkeypatch):
       # Change to main repo directory
       monkeypatch.chdir(mock_main_repo)

       # Call path resolution
       repo_root = locate_project_root()

       # Assert correct root found
       assert repo_root == mock_main_repo
       assert (repo_root / ".kittify").exists()
   ```
3. Run test: `pytest tests/unit/test_paths.py -v`

**Files**: `tests/unit/test_paths.py`

**Parallel?**: Yes (can run concurrently with T016, T017)

**Notes**: Use `monkeypatch.chdir()` to simulate execution context. Test both marker-based and git-based detection.

---

### T016 – Unit test: Path resolution from worktree

**Purpose**: Verify path resolution works correctly from worktree.

**Steps**:
1. In `tests/unit/test_paths.py`, add worktree test:
   ```python
   def test_locate_project_root_from_worktree(mock_worktree, monkeypatch):
       # Change to worktree directory
       monkeypatch.chdir(mock_worktree["worktree_path"])

       # Call path resolution
       repo_root = locate_project_root()

       # Assert walks up to main repo root
       assert repo_root == mock_worktree["repo_root"]
       assert (repo_root / ".kittify").exists()
   ```
2. Test worktree detection:
   ```python
   def test_is_worktree_context(mock_worktree):
       from specify_cli.core.paths import is_worktree_context

       assert is_worktree_context(mock_worktree["worktree_path"]) is True
       assert is_worktree_context(mock_worktree["repo_root"]) is False
   ```
3. Run test: `pytest tests/unit/test_paths.py::test_locate_project_root_from_worktree -v`

**Files**: `tests/unit/test_paths.py`

**Parallel?**: Yes (can run concurrently with T015, T017)

**Notes**: Critical test - worktree path resolution is the primary pain point being solved.

---

### T017 – Unit test: Broken symlink handling

**Purpose**: Verify graceful error handling for broken symlinks (doesn't crash).

**Steps**:
1. In `tests/unit/test_paths.py`, add broken symlink test:
   ```python
   import os

   def test_broken_symlink_handling(tmp_path):
       from specify_cli.core.paths import locate_project_root

       # Create broken symlink
       target = tmp_path / "nonexistent"
       link = tmp_path / "broken_link"
       link.symlink_to(target)

       # Verify is_symlink() returns True
       assert link.is_symlink()
       # Verify exists() returns False
       assert not link.exists()

       # Path resolution should handle gracefully
       # (either ignore broken symlink or raise clear error)
       try:
           locate_project_root()
       except FileNotFoundError as e:
           assert "broken symlink" in str(e).lower()
   ```
2. Run test: `pytest tests/unit/test_paths.py::test_broken_symlink_handling -v`

**Files**: `tests/unit/test_paths.py`

**Parallel?**: Yes (can run concurrently with T015, T016)

**Notes**: Validates pattern from commit d9a07fc. Test should either succeed (symlink ignored) or raise clear error (not generic crash).

---

## Test Strategy

**Unit Tests** (T015-T017):
- Path resolution from main repo ✅
- Path resolution from worktree ✅
- Broken symlink handling ✅
- Coverage target: 90%+ for `paths.py` enhancements

**Integration Tests**:
- Deferred to WP02-WP05 (command-level integration tests)

**Manual Tests** (T014):
- `spec-kitty agent --help` ✅
- `spec-kitty agent feature --help` ✅
- `spec-kitty agent tasks --help` ✅
- `spec-kitty agent context --help` ✅
- `spec-kitty agent release --help` ✅

**Commands to Run**:
```bash
# Unit tests
pytest tests/unit/test_paths.py -v

# Coverage check
pytest tests/unit/test_paths.py --cov=src/specify_cli/core/paths --cov-report=term-missing

# Manual smoke test
spec-kitty agent --help
```

---

## Risks & Mitigations

**Risk 1: Import chain breaks**
- **Symptom**: `ModuleNotFoundError` when running `spec-kitty agent`
- **Mitigation**: Test imports incrementally (`python -c "from specify_cli.cli.commands import agent"`), ensure all `__init__.py` files created

**Risk 2: Foundation delays block parallel work**
- **Symptom**: Phase 1 takes >2 days, WP02-WP05 cannot start
- **Mitigation**: Keep scope minimal (stubs only), prioritize T014 acceptance test, defer deep path logic if needed

**Risk 3: Path resolution edge cases**
- **Symptom**: Tests fail on specific platforms or directory structures
- **Mitigation**: Use pathlib (cross-platform), test both marker and git detection, handle gracefully

**Risk 4: Pytest fixtures don't work**
- **Symptom**: Unit tests can't create mock environments
- **Mitigation**: Use `tmp_path` fixture (pytest built-in), validate fixture structure before using

---

## Definition of Done Checklist

- [ ] All subtasks T001-T017 completed
- [ ] `spec-kitty agent --help` displays help with 4 subcommands
- [ ] Path resolution works from main repo (manual test + unit test)
- [ ] Path resolution works from worktree (manual test + unit test)
- [ ] Broken symlink handling doesn't crash (unit test)
- [ ] Test infrastructure created (`tests/unit/agent/`, `tests/integration/`)
- [ ] Pytest fixtures available for worktree testing
- [ ] 90%+ coverage for `paths.py` enhancements
- [ ] All imports work without errors
- [ ] No warnings or deprecations in test output
- [ ] Documentation: Updated quickstart.md if needed (checkpoint message)

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Manual test passes**: `spec-kitty agent --help` shows all subcommands
2. **Unit tests pass**: `pytest tests/unit/test_paths.py -v` all green
3. **No import errors**: `python -c "from specify_cli.cli.commands import agent"` succeeds
4. **Coverage sufficient**: `pytest --cov` shows 90%+ for `paths.py`

**What Reviewers Should Check**:
- Typer sub-app registration follows pattern from research.md
- Path resolution uses three-tier strategy (env var → git → marker)
- Broken symlink pattern matches commit d9a07fc
- Stub modules are minimal (no deep implementation leaking into Phase 1)
- Test fixtures enable both main repo and worktree simulation

**Context to Revisit**:
- Research findings (research.md) - path resolution validation
- Quickstart guide (quickstart.md) - Python migration patterns
- Recent git history - symlink handling precedent

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
