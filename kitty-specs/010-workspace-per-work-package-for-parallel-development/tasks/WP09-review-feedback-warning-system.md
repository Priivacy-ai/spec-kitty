---
work_package_id: WP09
title: Review Feedback Warning System
lane: done
history:
- timestamp: '2026-01-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: team
assignee: team
dependencies: [WP01, WP03, WP05]
phase: Phase 3 - Quality & Polish
review_status: ''
reviewed_by: ''
shell_pid: manual
subtasks:
- T079
- T080
- T081
- T082
- T083
- T084
- T085
---

# Work Package Prompt: WP09 – Review Feedback Warning System

**Implementation command:**
```bash
spec-kitty implement WP09 --base WP05
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

**Primary Goal**: Add warning system to implement and review workflows that alerts agents when dependent WPs need manual rebase after parent WP changes (git limitation).

**Success Criteria**:
- ✅ Implement command displays warning when resuming WP whose base has changed
- ✅ Review prompts include warning when WP has dependent WPs in progress
- ✅ Warnings include specific git rebase commands to execute
- ✅ get_dependents() function used to identify dependent WPs
- ✅ WP lane status checked to determine if dependents are in progress
- ✅ Warning display logic tested (unit tests for various scenarios)

---

## Context & Constraints

**Why warnings needed**: Git cannot automatically rebase dependent workspaces when parent changes (unlike jj which will solve this in future feature). Manual rebase required. Warnings ensure agents don't work on stale code.

**Reference Documents**:
- [spec.md](../spec.md) - User Story 6 (Review Feedback Dependency Warning), FR-016 through FR-018
- [plan.md](../plan.md) - Implementation Notes (review feedback handling)
- [quickstart.md](../quickstart.md) - Review Feedback Handling section

**Git Limitation**: When WP01 changes after WP02 is created from it:
```
WP01 modified → WP02 workspace has OLD version of WP01
Manual rebase required: cd .worktrees/011-feature-WP02 && git rebase 011-feature-WP01
```

**Warning Scenarios**:
1. **Review prompt**: WP01 enters review, WP02 (dependent) is in progress → warn reviewer
2. **Implement resume**: Agent resumes WP02, WP01 (base) has changed → warn implementer
3. **Review feedback**: WP01 moves back to planned (changes requested), WP02 in progress → warn both agents

---

## Subtasks & Detailed Guidance

### Subtask T079 – Add dependent WP detection to implement command

**Purpose**: Query dependency graph to find WPs that depend on current WP, used for warnings.

**Steps**:
1. In `src/specify_cli/cli/commands/implement.py`, import dependent detection:
   ```python
   from specify_cli.core.dependency_graph import (
       build_dependency_graph,
       get_dependents
   )
   ```

2. After workspace creation, check for dependents:
   ```python
   def check_for_dependents(feature_dir: Path, wp_id: str, console: Console):
       """Check if any WPs depend on this WP and warn if in progress."""
       # Build dependency graph
       graph = build_dependency_graph(feature_dir)

       # Get dependents
       dependents = get_dependents(wp_id, graph)
       if not dependents:
           return  # No dependents, no warnings needed

       # Check if any dependents are in progress (lane: planned, doing)
       in_progress_deps = []
       for dep_id in dependents:
           dep_file = find_wp_file(feature_dir, dep_id)
           dep_frontmatter = parse_wp_frontmatter(dep_file)
           if dep_frontmatter.get("lane") in ["planned", "doing", "for_review"]:
               in_progress_deps.append(dep_id)

       if in_progress_deps:
           console.print(f"\n[yellow]⚠️  Warning:[/yellow] {', '.join(in_progress_deps)} depend on {wp_id}")
           console.print("If you modify this WP, dependent WPs will need manual rebase")
   ```

3. Call this function in implement command after workspace creation

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (integrated into implement command)

---

### Subtask T080 – Display warning when resuming WP with changed base

**Purpose**: Detect if WP's base branch has changed since workspace was created, warn agent to rebase.

**Steps**:
1. In implement command, detect if workspace already exists (resuming work):
   ```python
   if workspace_path.exists():
       # Workspace exists - resuming work
       console.print(f"[cyan]Resuming work on {wp_id}[/cyan]")

       # Check if base branch has changed
       if base:
           base_branch = f"{feature_slug}-{base}"
           has_changes = check_base_branch_changed(workspace_path, base_branch)

           if has_changes:
               # Display rebase warning (T081)
               display_rebase_warning(workspace_path, wp_id, base_branch, console)
   ```

2. Implement base change detection:
   ```python
   def check_base_branch_changed(workspace_path: Path, base_branch: str) -> bool:
       """Check if base branch has commits not in current workspace."""
       # Get merge-base (common ancestor)
       result = subprocess.run(
           ["git", "merge-base", "HEAD", base_branch],
           cwd=workspace_path,
           capture_output=True,
           text=True
       )
       merge_base = result.stdout.strip()

       # Get base branch tip
       result = subprocess.run(
           ["git", "rev-parse", base_branch],
           cwd=workspace_path,
           capture_output=True,
           text=True
       )
       base_tip = result.stdout.strip()

       # If merge-base != base tip, base has new commits
       return merge_base != base_tip
   ```

**Files**: `src/specify_cli/cli/commands/implement.py`

**Parallel?**: No (sequential with T081)

---

### Subtask T081 – Include rebase command in warning

**Purpose**: Provide specific git rebase command in warnings so agents know exactly what to run.

**Steps**:
1. Implement warning display function:
   ```python
   def display_rebase_warning(
       workspace_path: Path,
       wp_id: str,
       base_branch: str,
       console: Console
   ):
       """Display warning about needing to rebase on changed base."""
       console.print(f"\n[bold yellow]⚠️  Base branch {base_branch} has changed[/bold yellow]")
       console.print(f"Your {wp_id} workspace may have outdated code from base\n")

       console.print("[cyan]Recommended action:[/cyan]")
       console.print(f"  cd {workspace_path}")
       console.print(f"  git rebase {base_branch}")
       console.print("  # Resolve any conflicts")
       console.print("  git add .")
       console.print("  git rebase --continue\n")

       console.print("[yellow]This is a git limitation.[/yellow]")
       console.print("Future jj integration will auto-rebase dependent workspaces.")
   ```

2. Call from implement command when resuming work and base has changed

**Files**: `src/specify_cli/cli/commands/implement.py`

**Example Warning Output**:
```
⚠️  Base branch 010-workspace-per-wp-WP01 has changed
Your WP02 workspace may have outdated code from base

Recommended action:
  cd .worktrees/010-workspace-per-wp-WP02
  git rebase 010-workspace-per-wp-WP01
  # Resolve any conflicts
  git add .
  git rebase --continue

This is a git limitation.
Future jj integration will auto-rebase dependent workspaces.
```

**Parallel?**: No (called by T080)

---

### Subtask T082 – Add dependent WP warnings to review prompts

**Purpose**: Update review workflow to warn when reviewing a WP that has dependent WPs in progress.

**Steps**:
1. This is primarily a template update (done in WP07), but add runtime logic:
2. In review command (if exists), or in review prompt template generation:
   ```python
   def generate_review_warnings(feature_dir: Path, wp_id: str) -> str:
       """Generate warning text for review prompts."""
       graph = build_dependency_graph(feature_dir)
       dependents = get_dependents(wp_id, graph)

       if not dependents:
           return ""

       # Check if any dependents are in progress
       in_progress = []
       for dep_id in dependents:
           dep_file = find_wp_file(feature_dir, dep_id)
           dep_meta = parse_wp_frontmatter(dep_file)
           if dep_meta.get("lane") in ["planned", "doing"]:
               in_progress.append(dep_id)

       if not in_progress:
           return ""

       warning = f"""
## ⚠️ Dependency Warning

{', '.join(in_progress)} depend on this WP ({wp_id}).

**If you request changes:**
- Dependent WPs will have outdated code
- Implementer must notify dependent WP agents to rebase
- Manual rebase command: cd .worktrees/###-feature-WPXX && git rebase ###-feature-{wp_id}

This is a git limitation. Future jj integration will auto-rebase.
"""
       return warning
   ```

3. Include warning in review prompt display or template

**Files**: Review command implementation or template generation

**Parallel?**: Can implement in parallel with T079-T081

---

### Subtask T083 – Display warning when reviewing WP with dependents in progress

**Purpose**: When WP enters review lane and has dependents actively being worked on, display warning.

**Steps**:
1. Add logic to lane transition (when moving to for_review):
   ```python
   def on_move_to_review(feature_dir: Path, wp_id: str, console: Console):
       """Display warnings when WP moves to for_review lane."""
       graph = build_dependency_graph(feature_dir)
       dependents = get_dependents(wp_id, graph)

       in_progress = [
           dep for dep in dependents
           if get_wp_lane(feature_dir, dep) in ["planned", "doing"]
       ]

       if in_progress:
           console.print(f"\n[yellow]⚠️  Dependency Alert[/yellow]")
           console.print(f"{', '.join(in_progress)} are in progress and depend on {wp_id}")
           console.print("If changes are requested during review:")
           console.print("  1. Notify dependent WP agents")
           console.print("  2. Dependent WPs will need manual rebase after changes")
           for dep in in_progress:
               console.print(f"     cd .worktrees/###-feature-{dep} && git rebase ###-feature-{wp_id}")
   ```

2. Integrate with workflow commands (src/specify_cli/cli/commands/agent/workflow.py)

**Files**: `src/specify_cli/cli/commands/agent/workflow.py` (implement/review commands)

**Parallel?**: Can implement in parallel with T079-T081

---

### Subtask T084 – Update WP prompt templates with rebase guidance

**Purpose**: Include dependency rebase guidance in WP prompt template so agents see it in their prompts.

**Steps**:
1. Open `.kittify/templates/task-prompt-template.md`
2. Add section after "Review Feedback" section:
   ```markdown
   ## ⚠️ Dependency Rebase Guidance

   **If this WP depends on other WPs** (check frontmatter `dependencies:` field):

   When a parent WP changes during review:
   1. You'll need to rebase your workspace to get latest changes
   2. Command: `cd .worktrees/###-feature-{{work_package_id}} && git rebase ###-feature-WPXX`
   3. Resolve any conflicts
   4. Continue work on updated foundation

   **Check if rebase needed**:
   ```bash
   cd .worktrees/###-feature-{{work_package_id}}
   git log --oneline main..{{base_branch}}  # Shows commits in base not in your workspace
   ```

   **If this WP has dependent WPs** (other WPs depend on this one):

   When you make changes:
   1. Notify agents working on dependent WPs
   2. They'll need to rebase their workspaces to get your changes
   3. This is a git limitation - future jj integration will auto-rebase
   ```

3. Template should include conditional text based on whether WP has dependencies or dependents

**Files**: `.kittify/templates/task-prompt-template.md`

**Parallel?**: Can update in parallel with T079-T083

**Note**: This template is used during WP prompt generation in `/spec-kitty.tasks`, so guidance will appear in all WP prompts going forward.

---

### Subtask T085 – Test warning display logic

**Purpose**: Write unit tests to validate warnings are displayed in correct scenarios.

**Steps**:
1. Create test file: `tests/specify_cli/test_review_warnings.py`
2. Test scenarios:
   - WP has dependents in progress → warning displayed
   - WP has dependents but all in done lane → no warning
   - WP has no dependents → no warning
   - Resuming WP whose base changed → warning displayed
   - Resuming WP whose base unchanged → no warning

**Example Test**:
```python
def test_warning_when_dependents_in_progress(tmp_path):
    """Test warning displays when WP has dependents in doing lane."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (no deps)
    create_wp_file(tasks_dir / "WP01.md", "WP01", [], lane="for_review")

    # Create WP02 (depends on WP01, in doing lane)
    create_wp_file(tasks_dir / "WP02.md", "WP02", ["WP01"], lane="doing")

    # Check for dependent warnings
    graph = build_dependency_graph(feature_dir)
    dependents = get_dependents("WP01", graph)

    assert "WP02" in dependents

    # Check if WP02 is in progress
    wp02_meta = parse_wp_frontmatter(tasks_dir / "WP02.md")
    assert wp02_meta["lane"] == "doing"

    # Warning should be displayed for WP01 review
```

**Files**: `tests/specify_cli/test_review_warnings.py`

**Parallel?**: Can write in parallel with implementation

---

## Implementation Flow

**Warning display points:**

1. **During implement (resuming work)**:
   ```
   spec-kitty implement WP02
   → Workspace exists (resuming)
   → Check if base (WP01) has changed
   → If yes, display rebase warning
   ```

2. **During review (WP entering review)**:
   ```
   spec-kitty agent workflow review WP01
   → Query dependents of WP01
   → Find dependents in lanes: planned, doing
   → Display warning: "WP02 in progress, will need rebase if changes requested"
   ```

3. **In WP prompts (static guidance)**:
   ```
   WP prompt includes section explaining:
   - When rebase is needed
   - How to check if base changed
   - Exact rebase commands
   ```

---

## Test Strategy

**Unit Tests**: `tests/specify_cli/test_review_warnings.py`

**Test Coverage**:
- Dependent detection logic (various lane states)
- Base change detection (git log comparison)
- Warning display formatting
- Integration with implement command
- Integration with workflow commands (implement/review)

**Execution**:
```bash
pytest tests/specify_cli/test_review_warnings.py -v
```

---

## Risks & Mitigations

**Risk 1: Warning not displayed**
- Impact: Agents work on stale code, miss parent WP changes
- Mitigation: Multiple warning points (implement, review, workflow commands), prominent display with Rich formatting

**Risk 2: False positive warnings**
- Impact: Warns about rebase when not needed, causes confusion
- Mitigation: Accurate base change detection (git merge-base comparison), only warn if base actually changed

**Risk 3: Rebase command incorrect**
- Impact: Agent runs wrong rebase command, breaks workspace
- Mitigation: Test rebase commands manually, include conflict resolution guidance

**Risk 4: Warning fatigue**
- Impact: Too many warnings, agents ignore them
- Mitigation: Only warn when actually needed (in-progress dependents, changed base), make warnings actionable

---

## Definition of Done Checklist

- [ ] Dependent WP detection added to implement command (T079)
- [ ] Base change detection implemented (T080)
- [ ] Rebase command included in warnings (T081)
- [ ] Review prompt warnings implemented (T082)
- [ ] Move-to-review warnings implemented (T083)
- [ ] WP prompt template updated with rebase guidance (T084)
- [ ] Warning display tests written and passing (T085)
- [ ] Manual test: Modify WP01, resume WP02, verify warning displayed
- [ ] Manual test: Review WP01 with WP02 in doing lane, verify warning displayed

---

## Review Guidance

**Reviewers should verify**:
1. **Warnings are prominent**: Use Rich formatting (yellow, bold) to catch attention
2. **Warnings are actionable**: Include specific commands to run
3. **Warnings are accurate**: Only display when condition actually met
4. **Git limitation acknowledged**: Warnings explain this will be solved by future jj integration

**Key Acceptance Checkpoints**:
- Create WP01, create WP02 --base WP01, modify WP01, resume WP02 → warning displayed
- Review WP01 with WP02 in progress → warning displayed
- Review WP01 with WP02 in done lane → no warning (not in progress)

**Manual Testing Commands**:
```bash
# Setup
/spec-kitty.specify "Test Feature"
/spec-kitty.tasks

# Implement WP01 and WP02
spec-kitty implement WP01
cd .worktrees/011-test-WP01 && echo "WP01" > file.txt && git add . && git commit -m "WP01"

spec-kitty implement WP02 --base WP01

# Modify WP01 (simulate review feedback)
cd .worktrees/011-test-WP01 && echo "WP01 v2" > file.txt && git add . && git commit -m "WP01 changes"

# Resume WP02 - should see warning
spec-kitty implement WP02
# Expected: "⚠️ Base branch 011-test-WP01 has changed. Consider rebasing..."
```

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

Move this WP between lanes using:
```bash
spec-kitty agent workflow implement WP09
```

Or edit the `lane:` field in frontmatter directly.
- 2026-01-08T10:56:39Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T11:01:02Z – unknown – lane=for_review – Implementation complete: warning system for dependent WPs and rebase guidance
- 2026-01-08T11:03:33Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T11:04:55Z – unknown – lane=done – Review passed - comprehensive warning system with tests
