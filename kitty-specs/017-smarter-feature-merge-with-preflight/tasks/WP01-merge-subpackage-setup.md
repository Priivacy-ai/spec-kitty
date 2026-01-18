---
work_package_id: "WP01"
title: "Merge Subpackage Setup"
phase: "Phase 0 - Foundation"
subtasks:
  - "T001"
  - "T002"
dependencies: []
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

# Work Package Prompt: WP01 – Merge Subpackage Setup

## Objectives & Success Criteria

Create the foundational structure for the new `merge/` subpackage and add `topological_sort()` to the dependency graph module.

**Success Criteria**:
- `from specify_cli.merge import *` imports without error
- `topological_sort()` correctly orders a DAG
- All module stubs exist and are importable

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - Architecture overview
- `src/specify_cli/core/dependency_graph.py` - Existing graph utilities to extend

**Constraints**:
- Follow existing code patterns in `src/specify_cli/`
- Use Python 3.11+ features (type hints, dataclasses)
- No new external dependencies

## Subtasks & Detailed Guidance

### Subtask T001 – Create merge/ subpackage structure

**Purpose**: Establish the directory and module structure for all merge-related functionality.

**Steps**:
1. Create directory `src/specify_cli/merge/`
2. Create `__init__.py` with public API exports (initially empty, will be populated as modules are implemented)
3. Create stub files for each module:
   - `preflight.py` - Pre-flight validation
   - `forecast.py` - Conflict prediction
   - `ordering.py` - Merge ordering
   - `status_resolver.py` - Status file auto-resolution
   - `state.py` - Merge state persistence
   - `executor.py` - Core execution logic

**Files**:
- `src/specify_cli/merge/__init__.py`
- `src/specify_cli/merge/preflight.py`
- `src/specify_cli/merge/forecast.py`
- `src/specify_cli/merge/ordering.py`
- `src/specify_cli/merge/status_resolver.py`
- `src/specify_cli/merge/state.py`
- `src/specify_cli/merge/executor.py`

**Parallel?**: Yes, can be done alongside T002

**Notes**:
- Each stub file should have a docstring describing its purpose
- Include `__all__ = []` in each stub (to be populated later)
- Add `from __future__ import annotations` for forward references

**Example stub**:
```python
"""Pre-flight validation for merge operations.

Implements FR-001 through FR-004: checking worktree status and target branch
divergence before any merge operation begins.
"""

from __future__ import annotations

__all__: list[str] = []
```

---

### Subtask T002 – Add topological_sort() to dependency_graph.py

**Purpose**: Enable dependency-ordered merge by providing topological sorting of the WP dependency graph.

**Steps**:
1. Open `src/specify_cli/core/dependency_graph.py`
2. Add `topological_sort()` function using Kahn's algorithm
3. Add to `__all__` exports
4. Add unit test in `tests/specify_cli/test_dependency_graph.py` (optional but recommended)

**Files**:
- `src/specify_cli/core/dependency_graph.py` (modify)

**Parallel?**: Yes, can be done alongside T001

**Implementation**:

```python
def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    """Return nodes in topological order (dependencies before dependents).

    Uses Kahn's algorithm:
    1. Find all nodes with no incoming edges (no dependencies)
    2. Remove them from graph, add to result
    3. Repeat until graph is empty

    Args:
        graph: Adjacency list where graph[node] = [dependencies]
               Note: This is REVERSE of typical adjacency (edges point to deps)

    Returns:
        List of node IDs in topological order

    Raises:
        ValueError: If graph contains a cycle (use detect_cycles() first)

    Example:
        >>> graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}
        >>> topological_sort(graph)
        ['WP01', 'WP02', 'WP03']
    """
    # Build in-degree map and reverse adjacency
    in_degree: dict[str, int] = {node: 0 for node in graph}
    reverse_adj: dict[str, list[str]] = {node: [] for node in graph}

    for node, deps in graph.items():
        in_degree[node] = len(deps)
        for dep in deps:
            if dep in reverse_adj:
                reverse_adj[dep].append(node)

    # Start with nodes that have no dependencies
    queue = [node for node, degree in in_degree.items() if degree == 0]
    queue.sort()  # Stable ordering for determinism

    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)

        # "Remove" this node by decrementing in-degree of dependents
        for dependent in sorted(reverse_adj.get(node, [])):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
                queue.sort()  # Maintain sorted order

    if len(result) != len(graph):
        raise ValueError("Graph contains a cycle - cannot topologically sort")

    return result
```

**Notes**:
- The existing `detect_cycles()` should be called before `topological_sort()` in production code
- Use sorted queue for deterministic ordering (same deps → alphabetical)
- Graph format: `{"WP01": [], "WP02": ["WP01"]}` means WP02 depends on WP01

## Definition of Done Checklist

- [ ] `src/specify_cli/merge/` directory exists with all module stubs
- [ ] Each stub has docstring and `__all__` export list
- [ ] `topological_sort()` added to `dependency_graph.py`
- [ ] Function handles empty graph, single node, linear chain, fan-out, and diamond patterns
- [ ] Function raises `ValueError` on cyclic input
- [ ] `__all__` in `dependency_graph.py` updated to include `topological_sort`

## Review Guidance

- Verify all imports work: `python -c "from specify_cli.merge import *"`
- Test topological sort with sample graphs:
  ```python
  from specify_cli.core.dependency_graph import topological_sort

  # Linear chain
  assert topological_sort({"A": [], "B": ["A"], "C": ["B"]}) == ["A", "B", "C"]

  # Fan-out
  assert topological_sort({"A": [], "B": ["A"], "C": ["A"]}) == ["A", "B", "C"]

  # Diamond
  result = topological_sort({"A": [], "B": ["A"], "C": ["A"], "D": ["B", "C"]})
  assert result.index("A") < result.index("B") < result.index("D")
  assert result.index("A") < result.index("C") < result.index("D")
  ```

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
