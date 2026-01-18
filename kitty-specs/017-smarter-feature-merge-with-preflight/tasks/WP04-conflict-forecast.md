---
work_package_id: "WP04"
title: "Conflict Forecast"
phase: "Phase 2 - User Story 2 (P2)"
subtasks:
  - "T007"
  - "T008"
  - "T009"
dependencies: ["WP01", "WP03"]
lane: "done"
assignee: ""
agent: "codex"
shell_pid: "9049"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-18T10:37:13Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Conflict Forecast

## Objectives & Success Criteria

Implement conflict prediction for `--dry-run` mode, showing which files will conflict before the merge begins.

**User Story**: As a developer, I want to see which files will conflict before merging so I can prepare for resolution or adjust my merge strategy.

**Success Criteria**:
- `spec-kitty merge --dry-run` shows files that will conflict
- Status files marked as "auto-resolvable" in forecast
- Conflicts grouped by file with WP attribution
- Merge order shown alongside conflict forecast

**Functional Requirements Addressed**: FR-005, FR-006, FR-007

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md` - User Story 2 acceptance scenarios
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - forecast.py design
- `kitty-specs/017-smarter-feature-merge-with-preflight/data-model.md` - ConflictPrediction entity

**Constraints**:
- Must work with git 2.30+ (merge-tree available in 2.38+, use fallback for older)
- Conflict detection is best-effort prediction, not guaranteed
- Integrate into executor's dry-run path

## Subtasks & Detailed Guidance

### Subtask T007 – Implement ConflictPrediction dataclass

**Purpose**: Define the data structure for predicted conflicts.

**Steps**:
1. Open `src/specify_cli/merge/forecast.py`
2. Add ConflictPrediction dataclass per data-model.md

**Files**:
- `src/specify_cli/merge/forecast.py`

**Parallel?**: Yes

**Implementation**:
```python
"""Conflict prediction for merge dry-run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["ConflictPrediction", "predict_conflicts", "is_status_file"]


@dataclass
class ConflictPrediction:
    """Predicted conflict for a file."""
    file_path: str
    conflicting_wps: list[str]  # WP IDs that modify this file
    is_status_file: bool  # True if matches status file pattern
    confidence: str  # "certain", "likely", "possible"

    @property
    def auto_resolvable(self) -> bool:
        """Status files can be auto-resolved."""
        return self.is_status_file
```

---

### Subtask T008 – Build file→WPs mapping via git diff

**Purpose**: Identify which files each WP modifies to find overlaps (FR-005).

**Steps**:
1. Add `build_file_wp_mapping()` function
2. For each WP, run `git diff --name-only target...branch`
3. Build dict mapping file path → list of WP IDs
4. Files with 2+ WPs are potential conflicts

**Files**:
- `src/specify_cli/merge/forecast.py`

**Parallel?**: Yes

**Implementation**:
```python
import subprocess


def build_file_wp_mapping(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    repo_root: Path,
) -> dict[str, list[str]]:
    """Build mapping of file paths to WPs that modify them.

    Args:
        wp_workspaces: List of (worktree_path, wp_id, branch_name)
        target_branch: Branch being merged into
        repo_root: Repository root for running git commands

    Returns:
        Dict mapping file_path → [wp_ids that modify it]
    """
    file_to_wps: dict[str, list[str]] = {}

    for _, wp_id, branch_name in wp_workspaces:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{target_branch}...{branch_name}"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        if line not in file_to_wps:
                            file_to_wps[line] = []
                        file_to_wps[line].append(wp_id)
        except Exception:
            continue  # Skip this WP if diff fails

    return file_to_wps


def predict_conflicts(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    repo_root: Path,
) -> list[ConflictPrediction]:
    """Predict which files will conflict during merge.

    Args:
        wp_workspaces: Ordered list of (path, wp_id, branch)
        target_branch: Branch being merged into
        repo_root: Repository root

    Returns:
        List of ConflictPrediction for files with potential conflicts
    """
    file_to_wps = build_file_wp_mapping(wp_workspaces, target_branch, repo_root)

    predictions = []
    for file_path, wp_ids in sorted(file_to_wps.items()):
        if len(wp_ids) >= 2:
            predictions.append(ConflictPrediction(
                file_path=file_path,
                conflicting_wps=wp_ids,
                is_status_file=is_status_file(file_path),
                confidence="possible",  # Can enhance with merge-tree
            ))

    return predictions
```

---

### Subtask T009 – Detect status file patterns

**Purpose**: Identify status files that can be auto-resolved.

**Steps**:
1. Add `is_status_file()` function
2. Match patterns: `kitty-specs/**/tasks/*.md` and `kitty-specs/**/tasks.md`
3. Use `fnmatch` for glob-style matching

**Files**:
- `src/specify_cli/merge/forecast.py`

**Parallel?**: Yes

**Implementation**:
```python
import fnmatch


STATUS_FILE_PATTERNS = [
    "kitty-specs/*/tasks/*.md",      # WP files: kitty-specs/017-feature/tasks/WP01.md
    "kitty-specs/*/tasks.md",        # Main tasks: kitty-specs/017-feature/tasks.md
    "kitty-specs/*/*/tasks/*.md",    # Nested: kitty-specs/features/017/tasks/WP01.md
    "kitty-specs/*/*/tasks.md",      # Nested main
]


def is_status_file(file_path: str) -> bool:
    """Check if file matches status file patterns.

    Status files contain lane/checkbox/history that can be auto-resolved.
    """
    for pattern in STATUS_FILE_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def display_conflict_forecast(
    predictions: list[ConflictPrediction],
    console,
) -> None:
    """Display conflict predictions with Rich formatting."""
    if not predictions:
        console.print("[green]No conflicts predicted[/green]")
        return

    console.print("\n[bold]Conflict Forecast[/bold]\n")

    auto_resolvable = [p for p in predictions if p.auto_resolvable]
    manual_required = [p for p in predictions if not p.auto_resolvable]

    if auto_resolvable:
        console.print("[dim]Auto-resolvable (status files):[/dim]")
        for pred in auto_resolvable:
            wps = ", ".join(pred.conflicting_wps)
            console.print(f"  {pred.file_path}: {wps}")

    if manual_required:
        console.print("\n[yellow]May require manual resolution:[/yellow]")
        for pred in manual_required:
            wps = ", ".join(pred.conflicting_wps)
            console.print(f"  {pred.file_path}: {wps} ({pred.confidence})")

    console.print()
```

## Definition of Done Checklist

- [ ] `ConflictPrediction` dataclass implemented
- [ ] `build_file_wp_mapping()` correctly identifies modified files per WP
- [ ] `is_status_file()` matches status file patterns
- [ ] `predict_conflicts()` returns predictions for overlapping files
- [ ] `display_conflict_forecast()` shows formatted output
- [ ] Status files marked as auto-resolvable
- [ ] Integrated into executor's dry-run path

## Review Guidance

**Acceptance Test**:
1. Create feature where WP01 and WP02 both modify `tests/conftest.py`
2. Create feature where WP01 and WP02 both modify `kitty-specs/.../tasks/WP01.md`
3. Run `spec-kitty merge --dry-run`
4. Verify: conftest.py listed as "manual required", tasks file listed as "auto-resolvable"

**Edge Cases**:
- File modified by only 1 WP → no conflict prediction
- All conflicts are status files → "All conflicts auto-resolvable"
- git diff fails → skip that WP gracefully

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T11:10:27Z – claude – shell_pid=17700 – lane=doing – Started implementation via workflow command
- 2026-01-18T11:12:29Z – claude – shell_pid=17700 – lane=for_review – Ready for review: Implemented conflict forecast with ConflictPrediction dataclass, file->WP mapping, status file detection, and executor integration
- 2026-01-18T11:15:26Z – codex – shell_pid=9049 – lane=doing – Started review via workflow command
- 2026-01-18T11:16:01Z – codex – shell_pid=9049 – lane=done – Review passed: conflict forecast integrated
