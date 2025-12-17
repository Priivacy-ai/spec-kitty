---
work_package_id: "WP02"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Feature Management Commands"
phase: "Phase 2 - Feature Commands (Stream A)"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "61618"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Feature Management Commands

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

**Goal**: Migrate feature lifecycle bash scripts to Python agent commands, enabling agents to create features, check prerequisites, and setup plans without path confusion.

**Success Criteria**:
- `spec-kitty agent create-feature "test-feature" --json` creates worktree and returns parseable JSON
- `spec-kitty agent check-prerequisites --json` validates feature structure and returns JSON
- `spec-kitty agent setup-plan --json` scaffolds plan template and returns JSON
- All commands work identically from main repo and worktree
- 90%+ test coverage for `feature.py` and `worktree.py`
- Bash scripts replaced: `create-new-feature.sh`, `check-prerequisites.sh`, `setup-plan.sh`

**Why This Matters**: Feature management is the entry point for all agent workflows. Until agents can reliably create and validate features, the entire spec-kitty process is blocked.

---

## Context & Constraints

**Prerequisites**:
- **WP01 complete** ✅ (foundation infrastructure, agent namespace registered, path resolution working)
- Bash scripts to replace:
  - `.kittify/scripts/bash/create-new-feature.sh`
  - `.kittify/scripts/bash/check-prerequisites.sh`
  - `.kittify/scripts/bash/setup-plan.sh`

**Related Documents**:
- Spec: `kitty-specs/008-unified-python-cli/spec.md` (FR-022, User Story 1)
- Plan: `kitty-specs/008-unified-python-cli/plan.md` (Phase 2 section, parallel work)
- Quickstart: `kitty-specs/008-unified-python-cli/quickstart.md` (bash → Python migration patterns)

**Stream Assignment**: **Stream A (Agent Alpha)** - Can run in parallel with WP03, WP04, WP05

**Files Owned by This Stream**:
- `src/specify_cli/cli/commands/agent/feature.py` ✅ (no conflicts)
- `src/specify_cli/core/worktree.py` ✅ (no conflicts)
- `tests/unit/agent/test_feature.py` ✅ (no conflicts)

**Constraints**:
- Must preserve all existing bash script functionality
- JSON output must be parseable by agents (valid JSON, no extra output)
- Must detect next feature number automatically
- Must handle Windows (file copy fallback for symlinks)
- Must work from both main repo and worktree

---

## Subtasks & Detailed Guidance

### T018 – Create worktree.py module

**Purpose**: Establish core utilities module for worktree management operations.

**Steps**:
1. Create `src/specify_cli/core/worktree.py`
2. Add module docstring:
   ```python
   """Worktree management utilities for spec-kitty feature development.

   This module provides functions for creating and managing git worktrees
   for parallel feature development. All functions are location-aware and
   work correctly whether called from main repository or existing worktree.
   """
   ```
3. Import dependencies:
   ```python
   from pathlib import Path
   import subprocess
   from typing import Tuple, Optional
   from .paths import locate_project_root
   ```

**Files**: `src/specify_cli/core/worktree.py`

**Notes**: This module will contain 4 functions (T019-T022). Keep functions pure (no CLI dependencies).

---

### T019 – Implement create_feature_worktree() in worktree.py

**Purpose**: Migrate bash worktree creation logic to Python.

**Steps**:
1. Read `.kittify/scripts/bash/create-new-feature.sh` to understand current logic
2. Implement function:
   ```python
   def create_feature_worktree(
       repo_root: Path,
       feature_slug: str,
       feature_number: Optional[int] = None
   ) -> Tuple[Path, Path]:
       """Create git worktree for feature development.

       Args:
           repo_root: Repository root path
           feature_slug: Feature identifier (e.g., "test-feature")
           feature_number: Optional feature number (auto-detected if None)

       Returns:
           Tuple of (worktree_path, feature_dir)
       """
       # Auto-detect feature number if not provided
       if feature_number is None:
           feature_number = get_next_feature_number(repo_root)

       # Format: 001-test-feature
       branch_name = f"{feature_number:03d}-{feature_slug}"

       # Create worktree at .worktrees/001-test-feature
       worktree_path = repo_root / ".worktrees" / branch_name

       # Git command: git worktree add <path> -b <branch>
       subprocess.run(
           ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
           cwd=repo_root,
           check=True
       )

       # Create feature directory structure
       feature_dir = worktree_path / "kitty-specs" / branch_name
       feature_dir.mkdir(parents=True, exist_ok=True)

       return (worktree_path, feature_dir)
   ```
3. Handle errors gracefully (branch exists, worktree exists)

**Files**: `src/specify_cli/core/worktree.py`

**Notes**: Use `subprocess.run()` with `check=True` to raise on git errors. Return absolute paths.

---

### T020 – Implement get_next_feature_number() in worktree.py

**Purpose**: Auto-detect next sequential feature number by scanning existing features.

**Steps**:
1. Implement function:
   ```python
   def get_next_feature_number(repo_root: Path) -> int:
       """Determine next sequential feature number.

       Scans kitty-specs/ directory for existing features (###-name format)
       and returns next number in sequence.

       Args:
           repo_root: Repository root path

       Returns:
           Next feature number (e.g., 9 if highest existing is 008)
       """
       specs_dir = repo_root / "kitty-specs"
       if not specs_dir.exists():
           return 1

       # Find all ###-* directories
       max_number = 0
       for item in specs_dir.iterdir():
           if item.is_dir() and item.name[:3].isdigit():
               number = int(item.name[:3])
               max_number = max(max_number, number)

       return max_number + 1
   ```
2. Test edge cases (no features yet, gaps in numbering)

**Files**: `src/specify_cli/core/worktree.py`

**Notes**: Simple directory scan, assumes ###-name format. If no features exist, return 1.

---

### T021 – Implement setup_feature_directory() in worktree.py

**Purpose**: Create standard feature directory structure with necessary files/symlinks.

**Steps**:
1. Implement function:
   ```python
   def setup_feature_directory(
       feature_dir: Path,
       create_symlinks: bool = True
   ) -> None:
       """Setup standard feature directory structure.

       Creates:
       - kitty-specs/###-name/ directory
       - Symlinks to .kittify/templates/ (or file copies on Windows)

       Args:
           feature_dir: Feature directory path
           create_symlinks: If True, create symlinks; else copy files
       """
       # Feature directory should already exist (created by T019)
       feature_dir.mkdir(parents=True, exist_ok=True)

       # Create subdirectories
       (feature_dir / "checklists").mkdir(exist_ok=True)
       (feature_dir / "research").mkdir(exist_ok=True)
       (feature_dir / "tasks").mkdir(exist_ok=True)

       # Create or symlink templates (if needed)
       # Note: Bash script may have specific template handling
   ```
2. Handle Windows symlink fallback (file copy)
3. Check if running on Windows: `import platform; platform.system() == "Windows"`

**Files**: `src/specify_cli/core/worktree.py`

**Notes**: Research EV009 validates Windows fallback pattern exists in codebase. Find existing pattern and reuse.

---

### T022 – Implement validate_feature_structure() in worktree.py

**Purpose**: Migrate `check-prerequisites.sh` validation logic to Python.

**Steps**:
1. Read `.kittify/scripts/bash/check-prerequisites.sh` for validation rules
2. Implement function:
   ```python
   def validate_feature_structure(
       feature_dir: Path,
       check_tasks: bool = False
   ) -> dict:
       """Validate feature directory structure and required files.

       Args:
           feature_dir: Feature directory path
           check_tasks: If True, validate tasks.md and task files

       Returns:
           Dictionary with validation results:
           {
               "valid": bool,
               "errors": [list of error messages],
               "warnings": [list of warning messages],
               "paths": {dict of important paths}
           }
       """
       errors = []
       warnings = []

       # Check required files exist
       spec_file = feature_dir / "spec.md"
       if not spec_file.exists():
           errors.append(f"Missing required file: spec.md")

       # Check directory structure
       required_dirs = ["checklists", "research"]
       for dir_name in required_dirs:
           if not (feature_dir / dir_name).exists():
               warnings.append(f"Missing recommended directory: {dir_name}")

       # Check task files if requested
       if check_tasks:
           tasks_file = feature_dir / "tasks.md"
           if not tasks_file.exists():
               errors.append(f"Missing required file: tasks.md")

       return {
           "valid": len(errors) == 0,
           "errors": errors,
           "warnings": warnings,
           "paths": {
               "feature_dir": str(feature_dir),
               "spec_file": str(spec_file) if spec_file.exists() else None,
           }
       }
   ```

**Files**: `src/specify_cli/core/worktree.py`

**Notes**: Return structured dict (easy to convert to JSON). Distinguish errors (blocking) vs warnings (non-blocking).

---

### T023 – Implement create-feature command in feature.py

**Purpose**: Create CLI command wrapper for `create_feature_worktree()`.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/feature.py` (stub from WP01)
2. Add command:
   ```python
   import json
   import typer
   from typing_extensions import Annotated
   from specify_cli.core.paths import locate_project_root
   from specify_cli.core.worktree import create_feature_worktree, get_next_feature_number
   from specify_cli.cli import console

   @app.command(name="create-feature")
   def create_feature(
       feature_slug: Annotated[str, typer.Argument(help="Feature slug (e.g., 'user-auth')")],
       json_output: Annotated[bool, typer.Option("--json")] = False,
   ) -> None:
       """Create new feature with worktree and directory structure.

       This command is designed for AI agents to call programmatically.

       Examples:
           spec-kitty agent create-feature "new-dashboard" --json
       """
       try:
           repo_root = locate_project_root()
           worktree_path, feature_dir = create_feature_worktree(repo_root, feature_slug)

           if json_output:
               print(json.dumps({
                   "result": "success",
                   "feature": feature_dir.name,
                   "worktree_path": str(worktree_path),
                   "feature_dir": str(feature_dir)
               }))
           else:
               console.print(f"[green]✓[/green] Feature created: {feature_dir.name}")
               console.print(f"   Worktree: {worktree_path}")
               console.print(f"   Directory: {feature_dir}")

       except Exception as e:
           if json_output:
               print(json.dumps({"error": str(e)}))
               raise typer.Exit(1)
           else:
               console.print(f"[red]Error:[/red] {e}")
               raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Notes**: Follow pattern from quickstart.md. JSON output ONLY prints JSON (no console messages mixed in).

---

### T024 – Implement check-prerequisites command

**Purpose**: Create CLI command for feature structure validation.

**Steps**:
1. In `feature.py`, add command:
   ```python
   @app.command(name="check-prerequisites")
   def check_prerequisites(
       json_output: Annotated[bool, typer.Option("--json")] = False,
       paths_only: Annotated[bool, typer.Option("--paths-only")] = False,
       include_tasks: Annotated[bool, typer.Option("--include-tasks")] = False,
   ) -> None:
       """Validate feature structure and prerequisites.

       This command is designed for AI agents to call programmatically.

       Examples:
           spec-kitty agent check-prerequisites --json
           spec-kitty agent check-prerequisites --paths-only --json
       """
       try:
           repo_root = locate_project_root()
           # Determine feature directory (main repo or worktree)
           # ... path resolution logic ...

           validation_result = validate_feature_structure(feature_dir, check_tasks=include_tasks)

           if json_output:
               if paths_only:
                   print(json.dumps(validation_result["paths"]))
               else:
                   print(json.dumps(validation_result))
           else:
               if validation_result["valid"]:
                   console.print("[green]✓[/green] Prerequisites check passed")
               else:
                   console.print("[red]✗[/red] Prerequisites check failed")
                   for error in validation_result["errors"]:
                       console.print(f"   • {error}")

       except Exception as e:
           if json_output:
               print(json.dumps({"error": str(e)}))
               raise typer.Exit(1)
           else:
               console.print(f"[red]Error:[/red] {e}")
               raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Notes**: Must detect if running in worktree or main repo (use `locate_project_root()` + path inspection).

---

### T025 – Implement setup-plan command

**Purpose**: Scaffold plan.md template (replaces `setup-plan.sh`).

**Steps**:
1. Read `.kittify/scripts/bash/setup-plan.sh` for template logic
2. In `feature.py`, add command:
   ```python
   @app.command(name="setup-plan")
   def setup_plan(
       json_output: Annotated[bool, typer.Option("--json")] = False,
   ) -> None:
       """Scaffold implementation plan template.

       This command is designed for AI agents to call programmatically.

       Examples:
           spec-kitty agent setup-plan --json
       """
       try:
           repo_root = locate_project_root()
           feature_dir = # ... detect feature dir ...

           plan_template = repo_root / ".kittify" / "templates" / "plan-template.md"
           plan_file = feature_dir / "plan.md"

           # Copy template to plan.md
           import shutil
           shutil.copy(plan_template, plan_file)

           if json_output:
               print(json.dumps({
                   "result": "success",
                   "plan_file": str(plan_file),
                   "feature_dir": str(feature_dir)
               }))
           else:
               console.print(f"[green]✓[/green] Plan scaffolded: {plan_file}")

       except Exception as e:
           if json_output:
               print(json.dumps({"error": str(e)}))
               raise typer.Exit(1)
           else:
               console.print(f"[red]Error:[/red] {e}")
               raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Notes**: Simple file copy. Template substitution (if needed) can be added later.

---

### T026 – Ensure dual output for feature commands

**Purpose**: Verify all commands support both JSON (agents) and Rich (humans) output modes.

**Steps**:
1. Review T023-T025 implementations
2. Verify pattern:
   - `--json` flag present on all commands ✅
   - JSON mode ONLY prints JSON (no console messages) ✅
   - Rich mode uses `console.print()` with colors ✅
   - Errors handled in both modes ✅
3. Test manually:
   ```bash
   spec-kitty agent create-feature "test" --json | python -m json.tool
   spec-kitty agent create-feature "test"  # Should show colors
   ```

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Notes**: JSON output must be valid JSON (agents parse with `json.loads()`). No extraneous output.

---

### T027 – Unit test: worktree.py utilities

**Purpose**: Test core worktree management functions in isolation.

**Steps**:
1. Create `tests/unit/agent/test_feature.py`
2. Test `get_next_feature_number()`:
   ```python
   def test_get_next_feature_number(tmp_path):
       from specify_cli.core.worktree import get_next_feature_number

       # Create mock specs directory
       specs = tmp_path / "kitty-specs"
       specs.mkdir()
       (specs / "001-first").mkdir()
       (specs / "002-second").mkdir()

       assert get_next_feature_number(tmp_path) == 3
   ```
3. Test `create_feature_worktree()` (mocked git)
4. Test `setup_feature_directory()`
5. Test `validate_feature_structure()`

**Files**: `tests/unit/agent/test_feature.py`

**Parallel?**: Yes (can run concurrently with T028-T030)

**Notes**: Use `tmp_path` fixture. Mock `subprocess.run()` for git commands to avoid actual git operations.

---

### T028 – Unit test: create-feature command

**Purpose**: Test CLI command logic for feature creation.

**Steps**:
1. In `test_feature.py`, test command:
   ```python
   from typer.testing import CliRunner
   from specify_cli.cli.commands.agent.feature import app

   runner = CliRunner()

   def test_create_feature_json_output(mock_main_repo, monkeypatch):
       monkeypatch.chdir(mock_main_repo)

       result = runner.invoke(app, ["create-feature", "test", "--json"])

       assert result.exit_code == 0
       output = json.loads(result.stdout)
       assert output["result"] == "success"
       assert "test" in output["feature"]
   ```
2. Test human output mode
3. Test error cases (invalid slug, git failure)

**Files**: `tests/unit/agent/test_feature.py`

**Parallel?**: Yes (can run concurrently with T027, T029, T030)

**Notes**: Use `typer.testing.CliRunner()` to invoke commands. Mock git operations to avoid side effects.

---

### T029 – Unit test: check-prerequisites command

**Purpose**: Test validation command with all flag combinations.

**Steps**:
1. Test `--json` flag
2. Test `--paths-only` flag
3. Test `--include-tasks` flag
4. Test combinations:
   ```python
   def test_check_prerequisites_all_flags(mock_worktree):
       result = runner.invoke(app, [
           "check-prerequisites",
           "--json",
           "--paths-only",
           "--include-tasks"
       ])
       assert result.exit_code == 0
       output = json.loads(result.stdout)
       assert "paths" in output
   ```

**Files**: `tests/unit/agent/test_feature.py`

**Parallel?**: Yes (can run concurrently with T027, T028, T030)

**Notes**: Test from both main repo and worktree contexts using fixtures.

---

### T030 – Unit test: setup-plan command

**Purpose**: Test plan scaffolding command.

**Steps**:
1. Test command creates plan.md:
   ```python
   def test_setup_plan_creates_file(mock_worktree):
       result = runner.invoke(app, ["setup-plan", "--json"])

       assert result.exit_code == 0
       output = json.loads(result.stdout)
       assert Path(output["plan_file"]).exists()
   ```
2. Test JSON output format
3. Test error case (template missing)

**Files**: `tests/unit/agent/test_feature.py`

**Parallel?**: Yes (can run concurrently with T027, T028, T029)

---

### T031 – Integration test: Create feature from main repo

**Purpose**: End-to-end test of feature creation workflow from main repository.

**Steps**:
1. Create `tests/integration/test_agent_workflows.py`
2. Test full workflow:
   ```python
   def test_create_feature_from_main_repo(tmp_path):
       # Setup mock main repo with git
       subprocess.run(["git", "init"], cwd=tmp_path, check=True)
       (tmp_path / ".kittify").mkdir()

       # Run create-feature command
       result = subprocess.run(
           ["spec-kitty", "agent", "create-feature", "test", "--json"],
           cwd=tmp_path,
           capture_output=True,
           text=True
       )

       assert result.returncode == 0
       output = json.loads(result.stdout)
       assert output["result"] == "success"

       # Verify worktree created
       worktree = Path(output["worktree_path"])
       assert worktree.exists()
       assert (worktree / "kitty-specs").exists()
   ```

**Files**: `tests/integration/test_agent_workflows.py`

**Parallel?**: Yes (can run concurrently with T032 after T023-T025 complete)

**Notes**: Requires real git operations. Use `tmp_path` with `git init` to create isolated test repo.

---

### T032 – Integration test: Create feature from worktree

**Purpose**: Verify feature commands work when executed from existing worktree.

**Steps**:
1. In `test_agent_workflows.py`, test worktree context:
   ```python
   def test_create_feature_from_worktree(tmp_path):
       # Setup main repo with existing worktree
       # ... create main repo ...
       # ... create first worktree ...

       # Run command from inside worktree
       result = subprocess.run(
           ["spec-kitty", "agent", "check-prerequisites", "--json"],
           cwd=first_worktree,
           capture_output=True,
           text=True
       )

       assert result.returncode == 0
       output = json.loads(result.stdout)
       # Should detect worktree context correctly
   ```

**Files**: `tests/integration/test_agent_workflows.py`

**Parallel?**: Yes (can run concurrently with T031)

**Notes**: Critical test - validates worktree-aware path resolution works end-to-end.

---

### T033 – Verify 90%+ coverage for feature.py

**Purpose**: Ensure test coverage meets quality requirement.

**Steps**:
1. Run coverage tool:
   ```bash
   pytest tests/unit/agent/test_feature.py \
     --cov=src/specify_cli/cli/commands/agent/feature \
     --cov=src/specify_cli/core/worktree \
     --cov-report=term-missing
   ```
2. Review coverage report
3. Add tests for uncovered branches if below 90%
4. Document any intentionally uncovered code (with justification)

**Files**: N/A (coverage analysis)

**Notes**: Target is 90%+ (per FR-026). If below target, identify gaps and add tests.

---

## Test Strategy

**Unit Tests**:
- `worktree.py` utilities (T027): All 4 functions covered
- CLI commands (T028-T030): All 3 commands with flag combinations
- Coverage target: 90%+ for `feature.py` and `worktree.py`

**Integration Tests**:
- Create feature from main repo (T031)
- Create feature from worktree (T032)

**Commands to Run**:
```bash
# Unit tests
pytest tests/unit/agent/test_feature.py -v

# Integration tests
pytest tests/integration/test_agent_workflows.py::test_create_feature -v

# Coverage check
pytest tests/unit/agent/test_feature.py \
  --cov=src/specify_cli/cli/commands/agent/feature \
  --cov=src/specify_cli/core/worktree \
  --cov-report=term-missing
```

---

## Risks & Mitigations

**Risk 1: Git worktree edge cases**
- **Mitigation**: Comprehensive error handling, test with broken worktrees

**Risk 2: Windows symlink fallback**
- **Mitigation**: Detect platform, use file copy on Windows (existing pattern)

**Risk 3: JSON parsing failures for agents**
- **Mitigation**: Validate JSON output with `python -m json.tool` in tests

---

## Definition of Done Checklist

- [ ] All subtasks T018-T033 completed
- [ ] All 3 commands implemented: `create-feature`, `check-prerequisites`, `setup-plan`
- [ ] Commands work from main repo (integration test passing)
- [ ] Commands work from worktree (integration test passing)
- [ ] JSON output mode functional and parseable
- [ ] Rich console output mode functional with colors
- [ ] 90%+ test coverage achieved (T033)
- [ ] No bash script dependencies remaining
- [ ] Documentation: Function docstrings complete

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. `spec-kitty agent create-feature "test" --json` returns valid JSON ✅
2. Integration tests pass from both contexts ✅
3. Coverage report shows 90%+ for feature.py and worktree.py ✅

**Context to Revisit**:
- Bash scripts being replaced (understand current logic)
- Quickstart guide (migration patterns)

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-17T21:39:48Z – claude – shell_pid=61618 – lane=doing – Started implementation
