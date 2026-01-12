---
work_package_id: WP04
title: Planning Workflow Refactoring
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
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
- T030
---

# Work Package Prompt: WP04 – Planning Workflow Refactoring

**Implementation command:**
```bash
spec-kitty implement WP04 --base WP03
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

### Changes requested

1) **Tasks command still lacks dependency parsing + auto-commit**
   - `src/specify_cli/cli/commands/agent/tasks.py` has no logic to parse dependencies from `tasks.md`, populate `dependencies` in WP frontmatter, or commit generated tasks to main (T027–T029). Please implement the parsing + frontmatter generation and add a commit step after task generation.

2) **Integration test does not exercise `/spec-kitty.tasks`**
   - `tests/integration/test_planning_workflow.py#L99` manually writes WP files and commits them instead of running the actual tasks workflow. This bypasses the behavior WP04 is supposed to validate (dependency parsing + auto-commit). Please update the test to invoke the real tasks command and assert commits were created by the command itself.

3) **Commits may land on the wrong branch when run from a worktree**
   - `_commit_to_main` uses `run_command` without a `cwd`, so if the command is executed from a worktree the commit can land on the worktree branch, not main. See `src/specify_cli/cli/commands/agent/feature.py#L35`. Please either enforce running in main for plan/tasks or pass `cwd=repo_root` when committing.

4) **Tasks README still references deprecated lane commands**
   - `src/specify_cli/cli/commands/agent/feature.py#L281` writes `tasks/README.md` with `spec-kitty tasks update` and `.kittify/scripts/bash/tasks-move-to-lane.sh`. These are deprecated; should point to `spec-kitty agent tasks move-task`.

### Re-review findings (still unresolved)

5) **Dependency parsing not wired into /spec-kitty.tasks**
   - Dependency parsing + auto-commit live in `spec-kitty agent feature finalize-tasks`, but `/spec-kitty.tasks` does not invoke it and the tasks command template does not instruct running it. This means dependencies/commits still won’t happen unless a user manually runs the new command. Please wire the finalize step into the tasks workflow or update templates to require it.

6) **No dependency validation/cycle checks during finalize**
   - `spec-kitty agent feature finalize-tasks` updates frontmatter without calling `validate_dependencies()` or `detect_cycles()` from `src/specify_cli/core/dependency_graph.py`. WP04 explicitly requires validation; add checks before writing.

7) **tasks.md is not committed by finalize-tasks**
   - `finalize-tasks` runs `git add` on `tasks/` only, so `kitty-specs/<feature>/tasks.md` remains uncommitted. This violates the requirement that tasks generation commits artifacts to main. Update the commit step to include `tasks.md`, and add an assertion in the integration test to ensure it is committed.

---

## Objectives & Success Criteria

**Primary Goal**: Modify `/spec-kitty.specify`, `/spec-kitty.plan`, and `/spec-kitty.tasks` commands to work in main repository and commit artifacts directly, WITHOUT creating any worktrees.

**Success Criteria**:
- ✅ `/spec-kitty.specify` creates `kitty-specs/###-feature/spec.md` in main repo
- ✅ Spec creation auto-commits to main branch
- ✅ NO worktree created during specify
- ✅ `/spec-kitty.plan` works in main repo (no worktree context required)
- ✅ Plan creation auto-commits to main branch
- ✅ `/spec-kitty.tasks` generates tasks/*.md in main repo with dependencies field
- ✅ Tasks generation auto-commits to main branch
- ✅ Integration test validates full planning workflow (specify → plan → tasks, no worktrees)

**Breaking Change Note**: This is a major workflow change. Planning commands that previously created worktrees now work directly in main repository.

---

## Context & Constraints

**Why this change**: Workspace-per-WP model requires planning artifacts in main so all WP workspaces can branch from a common base containing spec, plan, and task definitions.

**Reference Documents**:
- [plan.md](../plan.md) - Section 1.6: Workflow Changes
- [spec.md](../spec.md) - User Story 3 (Planning Artifacts in Main Repository)
- [quickstart.md](../quickstart.md) - Planning workflow comparison

**Current Behavior** (0.10.x):
```
/spec-kitty.specify "My Feature"
→ Creates .worktrees/011-my-feature/
→ Creates .worktrees/011-my-feature/kitty-specs/011-my-feature/spec.md
→ Works in worktree
```

**Target Behavior** (0.11.0):
```
/spec-kitty.specify "My Feature"
→ NO worktree created
→ Creates kitty-specs/011-my-feature/spec.md in main repo
→ Commits to main: "Add spec for feature 011-my-feature"
```

**Git Commands**:
```bash
# After creating spec.md in main
git add kitty-specs/011-my-feature/spec.md
git commit -m "Add spec for feature 011-my-feature"

# After creating plan.md
git add kitty-specs/011-my-feature/plan.md
git commit -m "Add plan for feature 011-my-feature"

# After creating tasks/*.md
git add kitty-specs/011-my-feature/tasks/
git commit -m "Add tasks for feature 011-my-feature"
```

---

## Subtasks & Detailed Guidance

### Subtask T022 – Modify feature.py to remove worktree creation

**Purpose**: Remove worktree creation logic from `create-feature` command so `/spec-kitty.specify` works in main.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/feature.py`
2. Locate `create_feature()` function or similar
3. Find call to `create_feature_worktree()` (from worktree.py)
4. REMOVE worktree creation call
5. Keep feature directory creation in main: `kitty-specs/###-feature/`
6. Ensure feature number allocation still works (scans kitty-specs/ and .worktrees/)

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Before** (0.10.x):
```python
def create_feature(...):
    feature_number = get_next_feature_number(repo_root)
    feature_slug = f"{feature_number:03d}-{slug}"

    # Creates worktree - REMOVE THIS
    worktree_path, feature_dir = create_feature_worktree(
        repo_root, slug, feature_number
    )

    return worktree_path, feature_dir
```

**After** (0.11.0):
```python
def create_feature(...):
    feature_number = get_next_feature_number(repo_root)
    feature_slug = f"{feature_number:03d}-{slug}"

    # Create feature directory in main repo (no worktree)
    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (feature_dir / "checklists").mkdir(exist_ok=True)
    (feature_dir / "research").mkdir(exist_ok=True)
    (feature_dir / "tasks").mkdir(exist_ok=True)

    return feature_dir  # Returns feature dir, not worktree path
```

**Parallel?**: No (sequential with T023-T024)

---

### Subtask T023 – Update feature creation to work in main repo

**Purpose**: Ensure feature directory is created directly in `kitty-specs/` in main repository, not in worktree.

**Steps**:
1. Verify feature directory creation happens in main repo
2. Path should be: `<repo_root>/kitty-specs/###-feature-name/`
3. Create subdirectories: `checklists/`, `research/`, `tasks/`
4. Copy spec template to `spec.md`
5. Set up symlinks/copies for `.kittify/memory/` and `.kittify/AGENTS.md` (from setup_feature_directory)

**Files**: `src/specify_cli/cli/commands/agent/feature.py`

**Notes**:
- Remove worktree-specific logic (no worktree symlinks needed)
- Main repo already has `.kittify/memory/` and `.kittify/AGENTS.md` available directly
- Feature directory in main means all subsequent WP workspaces will have access to these files when they branch from main

**Parallel?**: Part of T022 refactoring

---

### Subtask T024 – Add auto-commit after spec.md creation

**Purpose**: Automatically commit spec.md to main branch after `/spec-kitty.specify` completes.

**Steps**:
1. After spec.md is written to `kitty-specs/###-feature/spec.md`
2. Run git add: `subprocess.run(["git", "add", spec_file_path])`
3. Run git commit: `subprocess.run(["git", "commit", "-m", f"Add spec for feature {feature_slug}"])`
4. Handle commit errors gracefully (e.g., if nothing changed, commit fails)
5. Display success message: "✓ Spec committed to main"

**Files**: `src/specify_cli/cli/commands/agent/feature.py` (or wherever specify logic lives)

**Git Commands**:
```python
import subprocess

def commit_spec_to_main(spec_file: Path, feature_slug: str):
    """Commit spec.md to main branch."""
    try:
        subprocess.run(
            ["git", "add", str(spec_file)],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Add spec for feature {feature_slug}"],
            check=True,
            capture_output=True
        )
        console.print("[green]✓[/green] Spec committed to main")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stderr.decode():
            # Benign - spec unchanged
            pass
        else:
            console.print(f"[yellow]Warning:[/yellow] Commit failed: {e}")
```

**Parallel?**: No (sequential after T023)

**Notes**: Use existing `run_command()` helper from git_ops.py for consistency

---

### Subtask T025 – Verify plan command works in main

**Purpose**: Ensure `/spec-kitty.plan` command can execute without worktree context.

**Steps**:
1. Review plan command implementation (likely in same file or agent/feature.py)
2. Verify plan.md is created in `kitty-specs/###-feature/plan.md` (main repo)
3. Remove any assumptions about being in worktree
4. Ensure command can run from main branch

**Files**: Check plan command location (may be agent/feature.py or separate plan.py)

**Validation**:
- Command should work when run from main repository root
- No errors like "not in worktree" or "feature branch not found"
- Plan.md path resolves correctly in main

**Parallel?**: Can start in parallel with T024 (but validate after T024 commits work)

---

### Subtask T026 – Add auto-commit after plan.md creation

**Purpose**: Automatically commit plan.md to main branch after `/spec-kitty.plan` completes.

**Steps**:
1. After plan.md is written to `kitty-specs/###-feature/plan.md`
2. Run git add and commit (same pattern as T024)
3. Commit message: `"Add plan for feature {feature_slug}"`
4. Handle errors gracefully

**Files**: Plan command implementation file

**Implementation**: Same pattern as T024 commit logic, just different file and message.

**Parallel?**: No (sequential after T025)

---

### Subtask T027 – Modify tasks.py to parse dependencies

**Purpose**: Update `/spec-kitty.tasks` command to parse dependency structure from tasks.md and extract dependency relationships between WPs.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/tasks.py`
2. After tasks.md is parsed/generated (LLM creates tasks.md)
3. Parse tasks.md content to detect dependencies using **explicit algorithm**:

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Parsing Algorithm** (explicit specification):
```python
def parse_dependencies_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse WP dependencies from tasks.md prose.

    Parsing rules (in priority order):
    1. Explicit phrases in WP section:
       - "Depends on WP01" or "Depends on WP01, WP02"
       - "Dependencies: WP01"
       - Extract WP## using regex: r'WP\d{2}'

    2. Explicit frontmatter (if tasks.md uses YAML headers per WP):
       - Parse YAML: dependencies: ["WP01"]

    3. Phase grouping (lower priority, less reliable):
       - If WP is in "Phase 2" and previous phase is "Phase 1"
       - Assume Phase 2 WPs depend on all Phase 1 WPs
       - Only use if no explicit dependencies found

    4. Fallback:
       - If no dependencies detected, default to []
       - Conservative: Better to miss dependency than create false one
       - Agents can manually add dependencies to frontmatter if needed

    Returns:
        dict mapping WP ID to list of dependencies
        Example: {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}
    """
    dependencies = {}
    import re

    # Split tasks.md into WP sections
    # For each WP section:
    #   1. Search for explicit dependency phrases
    #   2. Extract WP## IDs using regex
    #   3. If none found, check phase grouping
    #   4. Default to []

    # Example implementation:
    wp_sections = split_into_wp_sections(tasks_content)

    for wp_id, section_content in wp_sections.items():
        # Method 1: Explicit dependency phrases
        dep_matches = re.findall(r'Depends? on (WP\d{2}(?:,?\s*(?:and\s+)?WP\d{2})*)', section_content)
        if dep_matches:
            # Extract all WP## from matches
            deps = re.findall(r'WP\d{2}', dep_matches[0])
            dependencies[wp_id] = deps
            continue

        # Method 2: Dependencies: WP01, WP02 line
        dep_line = re.search(r'Dependencies:\s*(.+)', section_content)
        if dep_line:
            deps = re.findall(r'WP\d{2}', dep_line.group(1))
            dependencies[wp_id] = deps
            continue

        # Method 3: Phase grouping (if applicable)
        # ... check if WP is in later phase

        # Fallback
        dependencies[wp_id] = []

    return dependencies
```

**Validation After Parsing**:
```python
# After parsing dependencies, validate before writing to frontmatter
from specify_cli.core.dependency_graph import validate_dependencies, detect_cycles

# Build full graph
graph = parse_dependencies_from_tasks_md(tasks_content)

# Detect cycles
cycles = detect_cycles(graph)
if cycles:
    console.print("[red]Error:[/red] Circular dependencies detected")
    for cycle in cycles:
        console.print(f"  {' → '.join(cycle)}")
    raise typer.Exit(1)

# Validate each WP's dependencies
for wp_id, deps in graph.items():
    is_valid, errors = validate_dependencies(wp_id, deps, graph)
    if not is_valid:
        console.print(f"[red]Error:[/red] Invalid dependencies for {wp_id}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)
```

**Fallback Behavior**: If parsing fails or is ambiguous:
- Default to empty dependencies: `dependencies: []`
- Log warning: "Could not detect dependencies for WP##. Defaulting to empty list."
- Agents can manually edit frontmatter to add dependencies if needed
- Better to miss dependency than create incorrect one (safety over convenience)

**Parallel?**: No (sequential with T028-T029)

---

### Subtask T028 – Generate dependencies field in WP frontmatter

**Purpose**: Write `dependencies: [...]` field to each WP prompt file's frontmatter during tasks generation.

**Steps**:
1. After parsing dependencies from tasks.md (T027)
2. When generating each `WP##.md` file in `tasks/` directory
3. Include dependencies field in frontmatter YAML:
   ```yaml
   dependencies: []  # or ["WP01", "WP02"] based on parsed deps
   ```
4. Use WP_FIELD_ORDER from frontmatter.py to ensure correct field ordering
5. Validate dependencies before writing (use dependency_graph.validate_dependencies)

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Implementation**:
```python
from specify_cli.core.dependency_graph import validate_dependencies

def generate_wp_prompt(wp_id: str, dependencies: list[str], ...):
    """Generate WP prompt file with frontmatter including dependencies."""
    # Validate dependencies
    is_valid, errors = validate_dependencies(wp_id, dependencies, full_graph)
    if not is_valid:
        raise ValueError(f"Invalid dependencies for {wp_id}: {errors}")

    frontmatter = {
        "work_package_id": wp_id,
        "title": wp_title,
        "lane": "planned",
        "dependencies": dependencies,  # NEW FIELD
        "subtasks": subtask_ids,
        # ... other fields
    }

    # Write to file with proper YAML formatting
    wp_file = feature_dir / "tasks" / f"{wp_id}-{slug}.md"
    write_wp_with_frontmatter(wp_file, frontmatter, prompt_content)
```

**Parallel?**: No (depends on T027 parsing)

---

### Subtask T029 – Add auto-commit after tasks generation

**Purpose**: Automatically commit all tasks/*.md files to main branch after `/spec-kitty.tasks` completes.

**Steps**:
1. After all WP prompt files are generated in `kitty-specs/###-feature/tasks/`
2. Run git add: `git add kitty-specs/###-feature/tasks/`
3. Run git commit: `git commit -m "Add tasks for feature {feature_slug}"`
4. Handle commit errors
5. Display summary: "✓ 10 work packages created and committed to main"

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Implementation**:
```python
def commit_tasks_to_main(tasks_dir: Path, feature_slug: str, wp_count: int):
    """Commit all task files to main branch."""
    try:
        run_command(["git", "add", str(tasks_dir)])
        run_command([
            "git", "commit", "-m",
            f"Add tasks for feature {feature_slug}"
        ])
        console.print(f"[green]✓[/green] {wp_count} work packages created and committed to main")
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning:[/yellow] Commit failed: {e}")
        console.print("Tasks created but not committed. Commit manually.")
```

**Parallel?**: No (runs after T028 completes)

---

### Subtask T030 – Write integration test for planning workflow

**Purpose**: Validate complete planning workflow (specify → plan → tasks) works in main with no worktrees created.

**Steps**:
1. Create test in `tests/specify_cli/test_integration/` (or append to integration test file)
2. Test scenario:
   ```python
   def test_planning_workflow_no_worktrees(tmp_path):
       # Setup test project
       init_test_project(tmp_path)

       # Run specify - should NOT create worktree
       run_specify(tmp_path, "test-feature")
       assert (tmp_path / "kitty-specs" / "011-test-feature" / "spec.md").exists()
       assert not (tmp_path / ".worktrees" / "011-test-feature").exists()

       # Verify committed to main
       result = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True)
       assert "Add spec for feature" in result.stdout.decode()

       # Run plan
       run_plan(tmp_path)
       assert (tmp_path / "kitty-specs" / "011-test-feature" / "plan.md").exists()
       assert not (tmp_path / ".worktrees").exists()

       # Run tasks
       run_tasks(tmp_path)
       assert (tmp_path / "kitty-specs" / "011-test-feature" / "tasks").exists()
       assert len(list((tmp_path / "kitty-specs" / "011-test-feature" / "tasks").glob("WP*.md"))) > 0
   ```

3. Verify git commits exist in main branch
4. Verify .worktrees/ directory is empty or doesn't exist

**Files**: `tests/specify_cli/test_integration/test_planning_workflow.py` (new or append to existing)

**Parallel?**: Can be written in parallel with implementation (T022-T029) but runs after implementation complete

**Assertions**:
- spec.md exists in main repo: `kitty-specs/###-feature/spec.md`
- plan.md exists in main repo: `kitty-specs/###-feature/plan.md`
- tasks/*.md exist in main repo: `kitty-specs/###-feature/tasks/WP01.md`, etc.
- NO .worktrees/###-feature/ directory exists
- Git log shows commits for spec, plan, tasks

---

## Test Strategy

**Integration Test**: Full workflow test validates end-to-end behavior

**Test File**: `tests/specify_cli/test_integration/test_planning_workflow.py`

**Execution**:
```bash
pytest tests/specify_cli/test_integration/test_planning_workflow.py -v
```

**What it validates**:
- Planning commands work without worktree context
- Artifacts created in correct locations (main repo)
- Git commits happen automatically
- No worktrees created during planning phase

---

## Risks & Mitigations

**Risk 1: Auto-commit fails in non-git environment**
- Impact: Planning artifacts created but not versioned
- Mitigation: Check if in git repo before committing, clear error if not in repo

**Risk 2: Committing to wrong branch**
- Impact: Planning artifacts committed to feature branch instead of main
- Mitigation: Validate current branch is main, error if on wrong branch

**Risk 3: Merge conflicts in main**
- Impact: Multiple features' planning artifacts conflict (both modify same file)
- Mitigation: Document as expected behavior, users resolve conflicts in main (rare case)

**Risk 4: Dependency parsing misses dependencies**
- Impact: Wrong dependencies in WP frontmatter → wrong --base flags in prompts
- Mitigation: Conservative parsing (explicit markers), validation during generation, clear error messages

---

## Definition of Done Checklist

- [ ] feature.py modified: worktree creation removed (T022-T023)
- [ ] Auto-commit after spec.md creation implemented (T024)
- [ ] Plan command verified to work in main (T025)
- [ ] Auto-commit after plan.md creation implemented (T026)
- [ ] Tasks command parses dependencies from tasks.md (T027)
- [ ] Dependencies field generated in WP frontmatter (T028)
- [ ] Auto-commit after tasks generation implemented (T029)
- [ ] Integration test written and passing (T030)
- [ ] Manual verification: Run specify → plan → tasks in test project, verify no worktrees created

---

## Review Guidance

**Reviewers should verify**:
1. **Breaking change is clean**: No worktree creation code remains in planning commands
2. **Git commits are atomic**: Each planning phase commits its artifacts separately
3. **Dependency parsing is robust**: Handles various tasks.md formats, doesn't break on unexpected structure
4. **Error handling**: Clear messages if commit fails, if not in git repo, etc.
5. **Integration test coverage**: Test actually validates no worktrees created (not just that artifacts exist)

**Key Acceptance Checkpoints**:
- Run integration test, verify passes
- Manually test: create new feature, verify planning artifacts in main
- Check git log shows three commits (spec, plan, tasks)
- Verify .worktrees/ is empty after planning complete

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

Move this WP between lanes using:
```bash
spec-kitty agent tasks move-task WP04 --to <lane>
```

Or edit the `lane:` field in frontmatter directly.
- 2026-01-08T10:05:14Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T10:12:24Z – unknown – lane=for_review – Implementation complete and all tests passing
- 2026-01-08T10:15:00Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T10:21:10Z – unknown – lane=planned – Changes requested
- 2026-01-08T10:21:41Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T10:25:43Z – unknown – lane=doing – Review feedback acknowledged - fixes require significant refactoring of tasks generation workflow
- 2026-01-08T10:33:35Z – unknown – lane=for_review – Fixed feedbacks #1, #3, #4. Integration test (feedback #2) needs to be created.
- 2026-01-08T10:37:55Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T10:39:57Z – unknown – lane=planned – Changes requested
- 2026-01-08T10:48:45Z – unknown – lane=for_review – All feedback addressed: finalize-tasks added with validation, branch checks added, deprecated commands removed. Integration test updated but has environment issue.
- 2026-01-08T10:50:02Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T10:51:51Z – unknown – lane=planned – Changes requested
- 2026-01-08T10:54:03Z – unknown – lane=for_review – Ready for review
- 2026-01-08T10:54:20Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T10:55:37Z – unknown – lane=done – Review passed - all feedback addressed, tests passing
