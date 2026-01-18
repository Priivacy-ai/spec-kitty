---
work_package_id: "WP02"
title: "Pre-flight Validation"
phase: "Phase 1 - User Story 1 (P1)"
subtasks:
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T026"
  - "T027"
dependencies: ["WP01"]
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "9049"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-18T10:37:13Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Pre-flight Validation

## Objectives & Success Criteria

Implement pre-flight validation that checks ALL worktrees and the target branch BEFORE any merge operation begins, displaying all issues with actionable remediation steps.

**User Story**: As a developer finishing a multi-WP feature, I want to see all blockers before the merge starts so I can fix them in one pass rather than discovering them one-by-one.

**Success Criteria**:
- Running `spec-kitty merge` on a feature with dirty worktrees shows all issues upfront
- Target branch divergence is detected and reported with remediation
- Pre-flight failure exits with non-zero status without modifying any branches
- New `--feature` flag allows merge from main branch

**Functional Requirements Addressed**: FR-001, FR-002, FR-003, FR-004, FR-025, FR-027

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md` - User Story 1 acceptance scenarios
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - PreflightResult design
- `kitty-specs/017-smarter-feature-merge-with-preflight/data-model.md` - WPStatus, PreflightResult entities
- `src/specify_cli/cli/commands/merge.py` - Existing merge implementation

**Constraints**:
- Must not break existing `--dry-run`, `--keep-branch` flags
- Use Rich console for formatted output
- Reuse `find_wp_worktrees()` from existing merge.py

## Subtasks & Detailed Guidance

### Subtask T003 – Implement WPStatus and PreflightResult dataclasses

**Purpose**: Define the data structures for pre-flight validation results.

**Steps**:
1. Open `src/specify_cli/merge/preflight.py`
2. Add dataclass imports and type definitions
3. Implement `WPStatus` and `PreflightResult` dataclasses per data-model.md

**Files**:
- `src/specify_cli/merge/preflight.py`

**Parallel?**: Yes

**Implementation**:
```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class WPStatus:
    """Status of a single WP worktree during pre-flight."""
    wp_id: str
    worktree_path: Path
    branch_name: str
    is_clean: bool
    error: str | None = None

@dataclass
class PreflightResult:
    """Result of pre-merge validation checks."""
    passed: bool
    wp_statuses: list[WPStatus] = field(default_factory=list)
    target_diverged: bool = False
    target_divergence_msg: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

---

### Subtask T004 – Implement worktree dirty check

**Purpose**: Check each WP worktree for uncommitted changes (FR-001).

**Steps**:
1. Add `check_worktree_status()` function
2. Use `git status --porcelain` to detect changes
3. Return `WPStatus` with `is_clean` and `error` fields

**Files**:
- `src/specify_cli/merge/preflight.py`

**Parallel?**: Yes

**Implementation**:
```python
import subprocess

def check_worktree_status(worktree_path: Path, wp_id: str, branch_name: str) -> WPStatus:
    """Check if a worktree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            check=False,
        )
        is_clean = not result.stdout.strip()
        error = None if is_clean else f"Uncommitted changes in {worktree_path.name}"
        return WPStatus(
            wp_id=wp_id,
            worktree_path=worktree_path,
            branch_name=branch_name,
            is_clean=is_clean,
            error=error,
        )
    except Exception as e:
        return WPStatus(
            wp_id=wp_id,
            worktree_path=worktree_path,
            branch_name=branch_name,
            is_clean=False,
            error=str(e),
        )
```

---

### Subtask T005 – Implement target branch divergence check

**Purpose**: Verify target branch can fast-forward to origin (FR-002).

**Steps**:
1. Add `check_target_divergence()` function
2. Compare local and remote refs using `git rev-list`
3. Return divergence status and message

**Files**:
- `src/specify_cli/merge/preflight.py`

**Parallel?**: Yes

**Implementation**:
```python
def check_target_divergence(target_branch: str, repo_root: Path) -> tuple[bool, str | None]:
    """Check if target branch has diverged from origin.

    Returns:
        Tuple of (has_diverged, message)
    """
    try:
        # Fetch latest refs (optional, may fail if offline)
        subprocess.run(
            ["git", "fetch", "origin", target_branch],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )

        # Count commits ahead/behind
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{target_branch}...origin/{target_branch}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, None  # No remote tracking, assume OK

        ahead, behind = map(int, result.stdout.strip().split())

        if behind > 0:
            return True, f"{target_branch} is {behind} commit(s) behind origin. Run: git checkout {target_branch} && git pull"

        return False, None

    except Exception:
        return False, None  # Assume OK if check fails
```

---

### Subtask T006 – Implement run_preflight() with formatted output

**Purpose**: Orchestrate all pre-flight checks and display results (FR-003, FR-004).

**Steps**:
1. Add `run_preflight()` function that calls check functions
2. Add `display_preflight_result()` for Rich console output
3. Show all issues with actionable remediation steps

**Files**:
- `src/specify_cli/merge/preflight.py`

**Parallel?**: No (depends on T003, T004, T005)

**Implementation**:
```python
from rich.console import Console
from rich.table import Table

def run_preflight(
    feature_slug: str,
    target_branch: str,
    repo_root: Path,
    wp_workspaces: list[tuple[Path, str, str]],  # (path, wp_id, branch)
) -> PreflightResult:
    """Run all pre-flight checks before merge.

    Args:
        feature_slug: Feature identifier
        target_branch: Branch to merge into
        repo_root: Repository root path
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples

    Returns:
        PreflightResult with all check outcomes
    """
    result = PreflightResult(passed=True)

    # Check all worktrees
    for wt_path, wp_id, branch in wp_workspaces:
        status = check_worktree_status(wt_path, wp_id, branch)
        result.wp_statuses.append(status)
        if not status.is_clean:
            result.passed = False
            result.errors.append(status.error or f"{wp_id} has uncommitted changes")

    # Check target divergence
    diverged, msg = check_target_divergence(target_branch, repo_root)
    result.target_diverged = diverged
    result.target_divergence_msg = msg
    if diverged:
        result.passed = False
        result.errors.append(msg or f"{target_branch} has diverged from origin")

    return result


def display_preflight_result(result: PreflightResult, console: Console) -> None:
    """Display pre-flight results with Rich formatting."""
    console.print("\n[bold]Pre-flight Check[/bold]\n")

    # WP status table
    table = Table(show_header=True, header_style="bold")
    table.add_column("WP")
    table.add_column("Status")
    table.add_column("Issue")

    for status in result.wp_statuses:
        icon = "[green]✓[/green]" if status.is_clean else "[red]✗[/red]"
        issue = status.error or ""
        table.add_row(status.wp_id, icon, issue)

    # Target branch status
    if result.target_diverged:
        table.add_row("Target", "[red]✗[/red]", result.target_divergence_msg or "Diverged")
    else:
        table.add_row("Target", "[green]✓[/green]", "")

    console.print(table)

    if not result.passed:
        console.print("\n[bold red]Pre-flight failed.[/bold red] Fix these issues before merging:\n")
        for i, error in enumerate(result.errors, 1):
            console.print(f"  {i}. {error}")
        console.print()
```

---

### Subtask T026 – Update merge.py CLI to call preflight

**Purpose**: Integrate pre-flight into the merge command flow.

**Steps**:
1. Import preflight module in merge.py
2. Call `run_preflight()` before any merge operation
3. Display results and exit if preflight fails

**Files**:
- `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (integration)

**Notes**:
- Insert preflight call after worktree detection, before any git checkout
- On failure, display results and `raise typer.Exit(1)`
- On success, proceed with existing merge flow

---

### Subtask T027 – Add --feature flag for main-branch invocation

**Purpose**: Allow `spec-kitty merge --feature <slug>` from main branch (FR-027).

**Steps**:
1. Add `--feature` flag to merge command
2. If on main and `--feature` provided, use that slug
3. If on main and no `--feature`, list available features or error

**Files**:
- `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (integration)

**Implementation**:
```python
# Add to merge() function parameters:
feature: str = typer.Option(None, "--feature", help="Feature slug when merging from main branch"),

# In detection logic:
if current_branch == target_branch:
    if feature:
        feature_slug = feature
        # Validate feature exists...
    else:
        console.print("[red]Error:[/red] On main branch. Use --feature <slug> to specify feature.")
        raise typer.Exit(1)
```

## Definition of Done Checklist

- [ ] `WPStatus` and `PreflightResult` dataclasses implemented
- [ ] `check_worktree_status()` detects uncommitted changes
- [ ] `check_target_divergence()` detects branch divergence
- [ ] `run_preflight()` collects all results
- [ ] `display_preflight_result()` shows formatted output with remediation
- [ ] Pre-flight integrated into merge.py (called before any merge)
- [ ] `--feature` flag works for main-branch invocation
- [ ] Pre-flight failure exits non-zero without modifying branches

## Review Guidance

**Acceptance Test**:
1. Create a feature with 2+ WP worktrees
2. Make uncommitted changes in 2 worktrees
3. Run `spec-kitty merge`
4. Verify: Both dirty worktrees listed, remediation shown, no merge attempted

**Edge Cases**:
- All worktrees clean → preflight passes, merge proceeds
- One worktree missing → error reported
- Network offline → divergence check skipped (assume OK)

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T10:50:03Z – claude – shell_pid=10043 – lane=doing – Started implementation via workflow command
- 2026-01-18T10:52:45Z – claude – shell_pid=10043 – lane=for_review – Ready for review: preflight validation + --feature flag
- 2026-01-18T10:53:51Z – codex – shell_pid=9049 – lane=doing – Started review via workflow command
- 2026-01-18T10:55:29Z – codex – shell_pid=9049 – lane=planned – Moved to planned
- 2026-01-18T10:58:15Z – codex – shell_pid=9049 – lane=doing – Started implementation via workflow command
