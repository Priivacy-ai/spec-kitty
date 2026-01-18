---
work_package_id: "WP06"
title: "Merge State & Resume"
phase: "Phase 4 - User Story 6 (P4)"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T025"
dependencies: ["WP03"]
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-18T10:37:13Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Merge State & Resume

## Objectives & Success Criteria

Implement merge state persistence and `--resume` capability for recovering from interrupted merges.

**User Story**: As a developer, I want to resume an interrupted merge without starting over so I don't lose progress on multi-WP features.

**Success Criteria**:
- Merge state saved to `.kittify/merge-state.json` after each WP
- `--resume` flag continues from last incomplete WP
- `--abort` flag clears state and resets to clean state
- State cleared automatically on successful completion
- Detects and handles git MERGE_HEAD state

**Functional Requirements Addressed**: FR-021, FR-022, FR-023, FR-024, FR-026

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md` - User Story 6 acceptance scenarios
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - state.py design
- `kitty-specs/017-smarter-feature-merge-with-preflight/data-model.md` - MergeState entity

**Constraints**:
- JSON file storage (not database)
- Must detect interrupted git merge state (MERGE_HEAD)
- State file location: `.kittify/merge-state.json`
- Compatible with both workspace-per-WP and legacy modes

## Subtasks & Detailed Guidance

### Subtask T017 – Implement MergeState dataclass

**Purpose**: Define the data structure for persisted merge state.

**Steps**:
1. Open `src/specify_cli/merge/state.py`
2. Add MergeState dataclass per data-model.md

**Files**:
- `src/specify_cli/merge/state.py`

**Parallel?**: Yes

**Implementation**:
```python
"""Merge state persistence for resume capability."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["MergeState", "save_state", "load_state", "clear_state", "has_active_merge"]


@dataclass
class MergeState:
    """Persisted state for resumable merge operations."""
    feature_slug: str
    target_branch: str
    wp_order: list[str]  # Ordered list of WP IDs to merge
    completed_wps: list[str] = field(default_factory=list)
    current_wp: str | None = None
    has_pending_conflicts: bool = False
    strategy: str = "merge"  # "merge", "squash", "rebase"
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MergeState":
        """Create from dict (loaded JSON)."""
        return cls(**data)

    @property
    def remaining_wps(self) -> list[str]:
        """WPs not yet merged."""
        completed_set = set(self.completed_wps)
        return [wp for wp in self.wp_order if wp not in completed_set]

    @property
    def progress_percent(self) -> float:
        """Completion percentage."""
        if not self.wp_order:
            return 0.0
        return len(self.completed_wps) / len(self.wp_order) * 100

    def mark_wp_complete(self, wp_id: str) -> None:
        """Mark a WP as successfully merged."""
        if wp_id not in self.completed_wps:
            self.completed_wps.append(wp_id)
        self.current_wp = None
        self.updated_at = datetime.utcnow().isoformat()

    def set_current_wp(self, wp_id: str) -> None:
        """Set the currently-merging WP."""
        self.current_wp = wp_id
        self.updated_at = datetime.utcnow().isoformat()
```

---

### Subtask T018 – Implement save_state() and load_state()

**Purpose**: Persist and restore merge state to/from JSON file (FR-021).

**Steps**:
1. Add `save_state()` function to write state to `.kittify/merge-state.json`
2. Add `load_state()` function to read and validate state
3. Handle missing file, invalid JSON gracefully

**Files**:
- `src/specify_cli/merge/state.py`

**Parallel?**: Yes

**Implementation**:
```python
STATE_FILE = ".kittify/merge-state.json"


def get_state_path(repo_root: Path) -> Path:
    """Get path to merge state file."""
    return repo_root / STATE_FILE


def save_state(state: MergeState, repo_root: Path) -> None:
    """Save merge state to JSON file.

    Args:
        state: MergeState to persist
        repo_root: Repository root path
    """
    state_path = get_state_path(repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state.updated_at = datetime.utcnow().isoformat()

    with open(state_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


def load_state(repo_root: Path) -> MergeState | None:
    """Load merge state from JSON file.

    Args:
        repo_root: Repository root path

    Returns:
        MergeState if file exists and is valid, None otherwise
    """
    state_path = get_state_path(repo_root)

    if not state_path.exists():
        return None

    try:
        with open(state_path) as f:
            data = json.load(f)
        return MergeState.from_dict(data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        # Invalid state file - return None, caller should clear
        return None


def has_active_merge(repo_root: Path) -> bool:
    """Check if there's an active merge state.

    Returns True if state file exists and has remaining WPs.
    """
    state = load_state(repo_root)
    if state is None:
        return False
    return len(state.remaining_wps) > 0
```

---

### Subtask T019 – Implement --resume flag detection and continuation

**Purpose**: Allow `spec-kitty merge --resume` to continue interrupted merge (FR-022).

**Steps**:
1. Add `--resume` flag to merge command
2. If `--resume` and state exists, load state and continue
3. If `--resume` and no state, error with message
4. Detect git MERGE_HEAD for mid-merge state

**Files**:
- `src/specify_cli/cli/commands/merge.py`
- `src/specify_cli/merge/state.py`

**Parallel?**: No (integration)

**Implementation**:
```python
import subprocess


def detect_git_merge_state(repo_root: Path) -> bool:
    """Check if git has an active merge in progress.

    Uses MERGE_HEAD presence to detect mid-merge state.
    """
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


# In merge.py CLI:
# Add to merge() parameters:
# resume: bool = typer.Option(False, "--resume", help="Resume interrupted merge"),

# In merge logic:
# if resume:
#     state = load_state(repo_root)
#     if state is None:
#         console.print("[red]No merge state to resume[/red]")
#         raise typer.Exit(1)
#
#     console.print(f"Resuming merge of {state.feature_slug}")
#     console.print(f"  Progress: {len(state.completed_wps)}/{len(state.wp_order)} WPs")
#     console.print(f"  Remaining: {', '.join(state.remaining_wps)}")
#
#     # Check for pending git merge
#     if detect_git_merge_state(repo_root):
#         console.print("[yellow]Git merge in progress - resolve conflicts first[/yellow]")
#         raise typer.Exit(1)
#
#     # Continue with remaining WPs
#     wp_workspaces = filter_remaining_wps(all_workspaces, state.remaining_wps)
```

---

### Subtask T020 – Implement clear_state()

**Purpose**: Clear state on success or `--abort` (FR-023, FR-026).

**Steps**:
1. Add `clear_state()` function to remove state file
2. Add `--abort` flag to merge command
3. Clear state after successful merge completion
4. Clear state when `--abort` is used

**Files**:
- `src/specify_cli/merge/state.py`
- `src/specify_cli/cli/commands/merge.py`

**Parallel?**: No (integration)

**Implementation**:
```python
def clear_state(repo_root: Path) -> bool:
    """Remove merge state file.

    Args:
        repo_root: Repository root path

    Returns:
        True if file was removed, False if it didn't exist
    """
    state_path = get_state_path(repo_root)

    if state_path.exists():
        state_path.unlink()
        return True
    return False


# In merge.py CLI:
# Add to merge() parameters:
# abort: bool = typer.Option(False, "--abort", help="Abort and clear merge state"),

# Handle abort:
# if abort:
#     state = load_state(repo_root)
#     if state is None:
#         console.print("[yellow]No merge state to abort[/yellow]")
#     else:
#         clear_state(repo_root)
#         console.print(f"[green]Merge state cleared for {state.feature_slug}[/green]")
#
#         # Also abort git merge if in progress
#         if detect_git_merge_state(repo_root):
#             subprocess.run(["git", "merge", "--abort"], cwd=str(repo_root))
#             console.print("[green]Git merge aborted[/green]")
#
#     raise typer.Exit(0)
```

---

### Subtask T025 – Integrate state persistence into executor

**Purpose**: Save state after each WP merge for recovery (FR-024).

**Steps**:
1. Import state module in executor.py
2. Create MergeState at start of merge
3. Save state before and after each WP merge
4. Update current_wp and completed_wps appropriately
5. Clear state on successful completion

**Files**:
- `src/specify_cli/merge/executor.py`
- `src/specify_cli/merge/state.py`

**Parallel?**: No (integration)

**Implementation outline**:
```python
from specify_cli.merge.state import (
    MergeState,
    save_state,
    load_state,
    clear_state,
)


def execute_merge(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    strategy: str,
    repo_root: Path,
    tracker: StepTracker,
    feature_slug: str,
    resume_state: MergeState | None = None,
) -> MergeResult:
    """Execute merge with state persistence."""

    # Initialize or resume state
    if resume_state:
        state = resume_state
    else:
        state = MergeState(
            feature_slug=feature_slug,
            target_branch=target_branch,
            wp_order=[wp_id for _, wp_id, _ in wp_workspaces],
            strategy=strategy,
        )
        save_state(state, repo_root)

    merged_wps = list(state.completed_wps)

    for wt_path, wp_id, branch in wp_workspaces:
        # Skip already completed WPs (resume case)
        if wp_id in state.completed_wps:
            continue

        # Mark current WP and save
        state.set_current_wp(wp_id)
        save_state(state, repo_root)

        tracker.step(f"Merging {wp_id}")

        try:
            # Execute merge for this WP
            result = merge_single_wp(wt_path, wp_id, branch, target_branch, strategy, repo_root)

            if not result.success:
                # Save state for resume
                state.has_pending_conflicts = True
                save_state(state, repo_root)
                return MergeResult(
                    success=False,
                    merged_wps=merged_wps,
                    failed_wp=wp_id,
                    error=result.error,
                )

            # Mark WP complete
            state.mark_wp_complete(wp_id)
            save_state(state, repo_root)
            merged_wps.append(wp_id)

        except Exception as e:
            state.has_pending_conflicts = True
            save_state(state, repo_root)
            return MergeResult(
                success=False,
                merged_wps=merged_wps,
                failed_wp=wp_id,
                error=str(e),
            )

    # All WPs merged successfully - clear state
    clear_state(repo_root)

    return MergeResult(
        success=True,
        merged_wps=merged_wps,
    )
```

## Definition of Done Checklist

- [ ] `MergeState` dataclass implemented with all fields
- [ ] `save_state()` writes to `.kittify/merge-state.json`
- [ ] `load_state()` reads and validates state
- [ ] `clear_state()` removes state file
- [ ] `--resume` flag continues from last incomplete WP
- [ ] `--abort` flag clears state and aborts git merge
- [ ] Git MERGE_HEAD detection works
- [ ] State saved after each WP merge
- [ ] State cleared on successful completion
- [ ] Invalid state handled gracefully (clear and restart)

## Review Guidance

**Acceptance Test**:
1. Start merge of 3-WP feature
2. After WP01 completes, Ctrl+C to interrupt
3. Verify `.kittify/merge-state.json` exists with WP01 in completed_wps
4. Run `spec-kitty merge --resume`
5. Verify: Merge continues from WP02, WP01 not re-merged
6. On completion, verify state file is deleted

**Edge Cases**:
- Resume with no state file → clear error message
- Corrupt state file → clear and start fresh with warning
- Git MERGE_HEAD present → pause, prompt user to resolve
- --abort with git merge in progress → abort both spec-kitty and git state

**State File Format**:
```json
{
  "feature_slug": "017-smarter-feature-merge-with-preflight",
  "target_branch": "main",
  "wp_order": ["WP01", "WP02", "WP03", "WP04", "WP05", "WP06"],
  "completed_wps": ["WP01", "WP02"],
  "current_wp": "WP03",
  "has_pending_conflicts": false,
  "strategy": "merge",
  "started_at": "2026-01-18T10:30:00Z",
  "updated_at": "2026-01-18T10:35:00Z"
}
```

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
