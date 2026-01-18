---
work_package_id: "WP03"
title: "Smart Merge Ordering"
phase: "Phase 2 - User Story 3 (P2)"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T021"
  - "T022"
  - "T023"
dependencies: ["WP01", "WP02"]
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

# Work Package Prompt: WP03 – Smart Merge Ordering

## Objectives & Success Criteria

Implement dependency-based merge ordering and refactor the merge execution into a dedicated executor module.

**User Story**: As a developer, I want WPs merged in dependency order rather than numerical order so that dependent WPs have the latest code from their dependencies.

**Success Criteria**:
- WPs with `dependencies: ["WP01"]` in frontmatter merge after WP01
- Circular dependencies detected and reported clearly
- Missing dependency info falls back to numerical order with warning
- Merge execution extracted to `executor.py` for modularity

**Functional Requirements Addressed**: FR-008, FR-009, FR-010, FR-011

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md` - User Story 3 acceptance scenarios
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - ordering.py and executor.py design
- `src/specify_cli/core/dependency_graph.py` - Existing graph utilities (build_dependency_graph, detect_cycles, topological_sort)

**Constraints**:
- Use `build_dependency_graph()` and `topological_sort()` from WP01
- Maintain backward compatibility with existing merge behavior
- Executor must handle both workspace-per-WP and legacy modes

## Subtasks & Detailed Guidance

### Subtask T010 – Implement get_merge_order()

**Purpose**: Determine WP merge order based on dependency graph (FR-008, FR-009).

**Steps**:
1. Open `src/specify_cli/merge/ordering.py`
2. Import dependency graph utilities
3. Implement `get_merge_order()` that builds graph and sorts topologically

**Files**:
- `src/specify_cli/merge/ordering.py`

**Parallel?**: Yes

**Implementation**:
```python
"""Merge ordering based on WP dependencies."""

from __future__ import annotations

from pathlib import Path

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    topological_sort,
)

__all__ = ["get_merge_order", "MergeOrderError"]


class MergeOrderError(Exception):
    """Error determining merge order."""
    pass


def get_merge_order(
    wp_workspaces: list[tuple[Path, str, str]],
    feature_dir: Path,
) -> list[tuple[Path, str, str]]:
    """Return WPs in dependency order (topological sort).

    Args:
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples
        feature_dir: Path to feature directory containing tasks/

    Returns:
        Same tuples reordered by dependency

    Raises:
        MergeOrderError: If circular dependency detected
    """
    # Build WP ID → workspace mapping
    wp_map = {wp_id: (path, wp_id, branch) for path, wp_id, branch in wp_workspaces}

    # Build dependency graph from task frontmatter
    graph = build_dependency_graph(feature_dir)

    # Check for missing WPs in graph (may have no frontmatter)
    for wp_id in wp_map:
        if wp_id not in graph:
            graph[wp_id] = []  # No dependencies

    # Detect cycles
    cycles = detect_cycles(graph)
    if cycles:
        cycle_str = " → ".join(cycles[0])
        raise MergeOrderError(f"Circular dependency detected: {cycle_str}")

    # Topological sort
    try:
        ordered_ids = topological_sort(graph)
    except ValueError as e:
        raise MergeOrderError(str(e)) from e

    # Filter to only WPs we have workspaces for, maintaining order
    result = []
    for wp_id in ordered_ids:
        if wp_id in wp_map:
            result.append(wp_map[wp_id])

    return result
```

---

### Subtask T011 – Add cycle detection error reporting

**Purpose**: Provide clear error messages when circular dependencies exist (FR-010).

**Steps**:
1. Enhance `get_merge_order()` cycle detection message
2. Show the full cycle path in the error
3. Ensure pre-flight surfaces this error clearly

**Files**:
- `src/specify_cli/merge/ordering.py`

**Parallel?**: Yes

**Notes**:
- The existing `detect_cycles()` returns list of cycles
- Format as "WP01 → WP02 → WP03 → WP01" to show the loop

---

### Subtask T012 – Fallback to numerical order

**Purpose**: When no dependency info exists, use WP number order (FR-011).

**Steps**:
1. Detect when graph has no edges (all WPs have empty dependencies)
2. Log a warning about missing dependency info
3. Return WPs sorted by ID (WP01, WP02, ...)

**Files**:
- `src/specify_cli/merge/ordering.py`

**Parallel?**: Yes

**Implementation**:
```python
def has_dependency_info(graph: dict[str, list[str]]) -> bool:
    """Check if any WP has declared dependencies."""
    return any(deps for deps in graph.values())

# In get_merge_order():
if not has_dependency_info(graph):
    # No dependency info - fall back to numerical order
    return sorted(wp_workspaces, key=lambda x: x[1])  # Sort by wp_id
```

---

### Subtask T021 – Extract merge logic to executor.py

**Purpose**: Create a dedicated module for merge execution, separating from CLI.

**Steps**:
1. Open `src/specify_cli/merge/executor.py`
2. Move `merge_workspace_per_wp()` logic from merge.py
3. Create `MergeExecutor` class or `execute_merge()` function
4. Keep merge.py as thin CLI wrapper

**Files**:
- `src/specify_cli/merge/executor.py`
- `src/specify_cli/cli/commands/merge.py` (modify)

**Parallel?**: No (requires WP01 structure)

**Implementation outline**:
```python
"""Core merge execution logic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from specify_cli.cli import StepTracker
from specify_cli.core.git_ops import run_command

__all__ = ["execute_merge", "MergeResult"]


@dataclass
class MergeResult:
    """Result of merge execution."""
    success: bool
    merged_wps: list[str]
    failed_wp: str | None = None
    error: str | None = None


def execute_merge(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    strategy: str,
    repo_root: Path,
    tracker: StepTracker,
    on_wp_merged: Callable[[str], None] | None = None,
) -> MergeResult:
    """Execute merge for all WPs.

    Args:
        wp_workspaces: Ordered list of (path, wp_id, branch) tuples
        target_branch: Branch to merge into
        strategy: "merge", "squash", or "rebase"
        repo_root: Repository root (for running commands)
        tracker: StepTracker for progress display
        on_wp_merged: Callback after each WP merges (for state updates)

    Returns:
        MergeResult with success status
    """
    # Implementation moves from merge_workspace_per_wp()
    ...
```

---

### Subtask T022 – Integrate preflight into executor

**Purpose**: Ensure executor calls preflight before any merge operation.

**Steps**:
1. Import preflight module in executor
2. Call `run_preflight()` at start of `execute_merge()`
3. Return early with error if preflight fails

**Files**:
- `src/specify_cli/merge/executor.py`

**Parallel?**: No (depends on T021)

---

### Subtask T023 – Integrate ordering into executor

**Purpose**: Use dependency-ordered WP list instead of sorted glob.

**Steps**:
1. Import ordering module in executor
2. Call `get_merge_order()` to reorder WPs
3. Use ordered list for merge loop

**Files**:
- `src/specify_cli/merge/executor.py`

**Parallel?**: No (depends on T021)

**Notes**:
- Display merge order to user before starting
- Catch `MergeOrderError` and display cycle info

## Definition of Done Checklist

- [ ] `get_merge_order()` implemented using topological sort
- [ ] Circular dependencies detected with clear error message
- [ ] Fallback to numerical order when no deps declared
- [ ] `executor.py` contains core merge logic
- [ ] Preflight integrated into executor
- [ ] Ordering integrated into executor
- [ ] `merge.py` is a thin CLI wrapper calling executor

## Review Guidance

**Acceptance Test**:
1. Create feature with WP frontmatter:
   - WP01: `dependencies: []`
   - WP02: `dependencies: ["WP01"]`
   - WP03: `dependencies: ["WP01"]`
   - WP04: `dependencies: ["WP02", "WP03"]`
2. Run `spec-kitty merge --dry-run`
3. Verify: Order shown is WP01 → WP02/WP03 → WP04

**Edge Cases**:
- No dependencies declared → numerical order
- WP02 depends on WP99 (missing) → error or skip
- Circular: WP01 → WP02 → WP01 → clear error message

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T10:54:04Z – claude – shell_pid=11026 – lane=doing – Started implementation via workflow command
- 2026-01-18T10:59:45Z – claude – shell_pid=11026 – lane=for_review – Ready for review: Implemented smart merge ordering (get_merge_order, cycle detection, numerical fallback) and extracted executor module with preflight/ordering integration
- 2026-01-18T11:05:45Z – codex – shell_pid=9049 – lane=doing – Started review via workflow command
- 2026-01-18T11:06:51Z – codex – shell_pid=9049 – lane=planned – Moved to planned
- 2026-01-18T11:09:18Z – codex – shell_pid=9049 – lane=doing – Started implementation via workflow command
- 2026-01-18T11:13:52Z – codex – shell_pid=9049 – lane=for_review – Ready for review: executor wired for both modes
- 2026-01-18T11:15:07Z – claude – shell_pid=19436 – lane=doing – Started review via workflow command
- 2026-01-18T11:19:29Z – claude – shell_pid=19436 – lane=planned – Moved to planned
- 2026-01-18T11:22:49Z – claude – shell_pid=20739 – lane=doing – Started implementation via workflow command
- 2026-01-18T11:24:57Z – claude – shell_pid=20739 – lane=for_review – Ready for review: Fixed test imports, all 26 tests pass
- 2026-01-18T11:49:21Z – codex – shell_pid=9049 – lane=doing – Started review via workflow command
