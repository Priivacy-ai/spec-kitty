# Data Model: Workspace-per-Work-Package

**Feature**: 010-workspace-per-work-package-for-parallel-development
**Date**: 2026-01-07

## Overview

This document defines the key entities and their relationships for the workspace-per-work-package feature. All entities are represented as filesystem artifacts (YAML frontmatter, directories, git refs) with no database storage.

---

## Entities

### WorkPackage

Represents a single unit of work within a feature.

**Storage**: YAML frontmatter in `kitty-specs/###-feature/tasks/WP##.md`

**Attributes**:

- `work_package_id` (string, required): Unique identifier within feature (e.g., "WP01", "WP02")
- `title` (string, required): Human-readable description
- `lane` (string, required): Current status ("planned", "doing", "for_review", "done")
- `dependencies` (list[string], **NEW**): List of WP IDs this WP depends on (e.g., `["WP01"]`)
- `subtasks` (list[string], optional): Subtask identifiers
- `phase` (string, optional): Grouping label
- `assignee` (string, optional): Assigned person/team
- `agent` (string, optional): Implementing AI agent

**Relationships**:

- **depends_on**: References to other WorkPackages via `dependencies` field
- **depended_by**: Inverse relationship (computed, not stored)
- **workspace**: Associated Worktree entity (exists if WP is implemented)

**Validation Rules**:

- `work_package_id` must match filename pattern `WP##-title.md`
- `dependencies` must reference valid WP IDs within same feature
- Cannot depend on self (`WP01` depending on `WP01` is invalid)
- Dependency graph must be acyclic (no circular dependencies)

**Example**:

```yaml
---
work_package_id: "WP02"
title: "Build API Endpoints"
lane: "planned"
dependencies: ["WP01"]
subtasks: ["T001", "T002"]
phase: "Phase 2 - Implementation"
assignee: ""
agent: "claude"
---
```

---

### Worktree

Represents a git worktree for a single work package implementation.

**Storage**: Filesystem directory at `.worktrees/###-feature-WP##/` + git ref at `.git/worktrees/###-feature-WP##/`

**Attributes**:

- `path` (Path): Filesystem location (e.g., `.worktrees/010-workspace-per-wp-WP01/`)
- `branch_name` (string): Git branch name (e.g., `010-workspace-per-wp-WP01`)
- `base_branch` (string): Branch this worktree branched from (`main` or another WP's branch)
- `wp_id` (string): Associated work package ID (e.g., `WP01`)
- `feature_number` (string): Feature identifier (e.g., `010`)
- `created_at` (datetime): Worktree creation timestamp (git metadata)

**Relationships**:

- **work_package**: References WorkPackage entity via `wp_id`
- **parent_worktree**: References Worktree entity via `base_branch` (if base is another WP)

**Lifecycle**:

1. Created: `spec-kitty implement WP##` creates worktree
2. Active: Agent works in worktree, commits to branch
3. Merged: `spec-kitty merge` merges branch to main
4. Removed: `git worktree remove` deletes filesystem directory

**Detection**:

- Legacy worktree: `.worktrees/###-feature/` (no `-WP##` suffix)
- New worktree: `.worktrees/###-feature-WP##/` (with WP suffix)

---

### DependencyGraph

Represents the relationships between work packages in a feature.

**Storage**: Computed in-memory from WP frontmatter, not persisted as separate file

**Attributes**:

- `adjacency_list` (dict[str, list[str]]): Maps WP ID → list of WP IDs it depends on
  - Example: `{"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"], "WP04": ["WP02"]}`
- `feature_dir` (Path): Feature directory containing WPs
- `cycles` (list[list[str]] | None): Detected circular dependencies (None if acyclic)

**Computed Properties**:

- `inverse_graph` (dict[str, list[str]]): Maps WP ID → list of WP IDs that depend on it
  - Example: `{"WP01": ["WP02", "WP03"], "WP02": ["WP04"]}`
  - Used for review feedback warnings ("WP02, WP03 depend on WP01")

**Operations**:

- `build_graph(feature_dir: Path)`: Parse all WP frontmatter, build adjacency list
- `detect_cycles()`: Run DFS to find circular dependencies
- `get_dependents(wp_id: str)`: Query inverse graph
- `validate()`: Check for invalid references, self-dependencies, cycles

**Example Graph**:

```python
# Feature with 4 WPs: WP01 → WP02 → WP04
#                     WP01 → WP03
graph = DependencyGraph(feature_dir)
graph.adjacency_list = {
    "WP01": [],
    "WP02": ["WP01"],
    "WP03": ["WP01"],
    "WP04": ["WP02"]
}
graph.inverse_graph = {
    "WP01": ["WP02", "WP03"],
    "WP02": ["WP04"],
    "WP03": [],
    "WP04": []
}
graph.cycles = None  # Acyclic graph
```

---

### Feature

Represents a Spec Kitty feature with planning artifacts and associated WP worktrees.

**Storage**: Directory at `kitty-specs/###-feature-name/` + multiple `.worktrees/###-feature-WP##/` directories

**Attributes**:

- `feature_number` (string): Numeric identifier (e.g., "010")
- `slug` (string): Full feature identifier (e.g., "010-workspace-per-wp")
- `spec_path` (Path): Path to spec.md in main repo
- `plan_path` (Path): Path to plan.md in main repo
- `tasks_dir` (Path): Path to tasks/ directory in main repo
- `worktrees` (list[Worktree]): List of WP worktrees for this feature
- `model_type` (string): "legacy" or "workspace-per-wp"

**Detection Logic**:

```python
def detect_feature_model(feature_number: str) -> str:
    """Detect if feature uses legacy or workspace-per-wp model."""
    # Check .worktrees/ for pattern
    legacy_path = .worktrees/{feature_number}-*/ (single dir, no -WP## suffix)
    new_paths = .worktrees/{feature_number}-*-WP##/ (multiple dirs with WP suffix)

    if new_paths exist:
        return "workspace-per-wp"
    elif legacy_path exists:
        return "legacy"
    else:
        return "unknown"  # Planning only, not yet implemented
```

**Relationships**:

- **work_packages**: One-to-many with WorkPackage entities (via tasks/*.md files)
- **worktrees**: One-to-many with Worktree entities (via `.worktrees/` directories)

---

## Dependency Graph Algorithms

### Cycle Detection (DFS-based)

**Algorithm**: Depth-first search with coloring (white/gray/black)

**Pseudocode**:

```
function detect_cycles(graph):
    color = {wp: WHITE for all wp in graph}
    cycles = []

    for wp in graph:
        if color[wp] == WHITE:
            dfs(wp, color, [], cycles)

    return cycles if cycles else None

function dfs(node, color, path, cycles):
    color[node] = GRAY
    path.append(node)

    for neighbor in graph[node]:
        if color[neighbor] == GRAY:
            # Back edge found - cycle detected
            cycle_start = path.index(neighbor)
            cycles.append(path[cycle_start:] + [neighbor])
        elif color[neighbor] == WHITE:
            dfs(neighbor, color, path, cycles)

    path.pop()
    color[node] = BLACK
```

**Complexity**: O(V + E) where V = number of WPs, E = number of dependencies

**Test Cases**:

1. No cycles: `{"WP01": [], "WP02": ["WP01"]}` → None
2. Simple cycle: `{"WP01": ["WP02"], "WP02": ["WP01"]}` → `[["WP01", "WP02", "WP01"]]`
3. Complex cycle: `{"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"], "WP04": ["WP03", "WP01"]}` → No cycles (valid DAG)

### Dependent Lookup

**Algorithm**: Inverse graph construction

**Pseudocode**:

```
function build_inverse_graph(graph):
    inverse = {wp: [] for all wp in graph}

    for wp in graph:
        for dependency in graph[wp]:
            inverse[dependency].append(wp)

    return inverse

function get_dependents(wp_id, graph):
    inverse = build_inverse_graph(graph)
    return inverse[wp_id]
```

**Use Case**: Review feedback warnings

- WP01 moves to `for_review`
- Query: `get_dependents("WP01")` → `["WP02", "WP03"]`
- Display: "⚠️ WP02, WP03 depend on WP01. If changes requested, they'll need rebase."

---

## State Transitions

### WorkPackage Lane Transitions

```
planned → doing → for_review → done
   ↑         ↓         ↓
   └─────────┴─────────┘
   (review feedback loop)
```

**Dependency-Aware Transitions**:

- Moving WP01 from `doing` → `for_review`: Check for dependents, add warning if found
- Moving WP01 from `for_review` → `planned`: Warn dependents about upcoming changes
- Moving WP02 to `doing` when WP01 (dependency) is not `done`: Allowed, but warn about potential rebase needs

### Worktree Lifecycle

```
Not exists → Created → Active → Merged → Removed
              ↓         ↓         ↓
         (implement) (commits) (merge)
```

**Creation Triggers**:

- User/agent runs `spec-kitty implement WP##`
- Workspace doesn't exist yet
- Dependencies satisfied (if `--base` specified, base workspace exists)

**Removal Triggers**:

- Feature merged to main: `spec-kitty merge` optionally removes all WP worktrees
- Manual cleanup: `git worktree remove .worktrees/###-feature-WP##/`

---

## Dashboard Compatibility Requirements

**Note**: Dashboard implementation is out of scope for this feature, but design requirements documented here for future dashboard updates.

### Detection Requirements

Dashboard must detect and display:

1. **Legacy features** (pre-0.11.0):
   - Pattern: `.worktrees/###-feature/` (single worktree)
   - Display: Single worktree with all WPs in tasks/ directory

2. **Workspace-per-WP features** (0.11.0+):
   - Pattern: `.worktrees/###-feature-WP##/` (multiple worktrees)
   - Display: List of WP worktrees, each with status

3. **Planning-only features** (no worktrees yet):
   - Pattern: `kitty-specs/###-feature/` exists in main, no `.worktrees/###-feature*/` directories
   - Display: Feature in planning phase, no implementations started

4. **Merged features** (no worktrees, in main branch):
   - Pattern: `kitty-specs/###-feature/` in main, no worktrees, all WPs in `done` lane
   - Display: Completed feature

### WP Location Logic

**Where to find WPs:**

- **Always** read WP files from `kitty-specs/###-feature/tasks/WP##.md` in main repository
- Worktree structure (`.worktrees/###-feature-WP##/`) is for implementation isolation only
- WP frontmatter (lane, dependencies) is source of truth
- Each worktree contains full checkout of `kitty-specs/###-feature/` but dashboard reads from main

**Why this matters**: Prevents dashboard from scanning multiple worktrees for the same WP files. Main repo is canonical.

---

## Appendix: Migration Checklist

**For implementers - verify ALL items updated:**

### Agent Template Updates (12 total)

- [ ] `.claude/commands/specify.md` - Remove worktree creation
- [ ] `.claude/commands/plan.md` - Remove worktree reference
- [ ] `.claude/commands/tasks.md` - Add dependency generation instructions
- [ ] `.claude/commands/implement.md` - NEW file with --base flag docs

- [ ] `.github/prompts/` - (same 4 files)
- [ ] `.gemini/commands/` - (same 4 files)
- [ ] `.cursor/commands/` - (same 4 files)
- [ ] `.qwen/commands/` - (same 4 files)
- [ ] `.opencode/command/` - (same 4 files)
- [ ] `.windsurf/workflows/` - (same 4 files)
- [ ] `.codex/prompts/` - (same 4 files)
- [ ] `.kilocode/workflows/` - (same 4 files)
- [ ] `.augment/commands/` - (same 4 files)
- [ ] `.roo/commands/` - (same 4 files)
- [ ] `.amazonq/prompts/` - (same 4 files)

**Total**: 48 template files (4 files × 12 agents)

### Code Changes

- [ ] `src/specify_cli/core/dependency_graph.py` - NEW module
- [ ] `src/specify_cli/core/worktree.py` - Remove `create_feature_worktree`, add `create_wp_worktree`
- [ ] `src/specify_cli/core/git_ops.py` - Add WP worktree helpers
- [ ] `src/specify_cli/cli/commands/implement.py` - NEW command
- [ ] `src/specify_cli/cli/commands/agent/feature.py` - Remove worktree creation
- [ ] `src/specify_cli/cli/commands/agent/tasks.py` - Add dependency parsing, frontmatter generation
- [ ] `src/specify_cli/cli/commands/merge.py` - Add workspace-per-WP validation
- [ ] `src/specify_cli/frontmatter.py` - Add dependencies field
- [ ] `src/specify_cli/upgrade/migrations/m_0_11_0_workspace_per_wp.py` - NEW migration

### Test Coverage

- [ ] `tests/specify_cli/test_dependency_graph.py` - Unit tests (write FIRST)
- [ ] `tests/specify_cli/test_workspace_per_wp_migration.py` - Migration tests (write FIRST)
- [ ] `tests/specify_cli/test_integration/test_workspace_per_wp_workflow.py` - Integration tests

**Test coverage target**: >90% for dependency_graph.py, 100% for migration logic

---

## Example Scenarios

### Scenario 1: Simple Linear Dependency

**tasks.md structure:**

```markdown
## Phase 1 - Foundation
- WP01: Setup database schema
  - T001: Define user table
  - T002: Define product table

## Phase 2 - API (depends on Phase 1)
- WP02: Create API endpoints
  - T003: User endpoints
  - T004: Product endpoints
```

**Generated WP frontmatter:**

```yaml
# WP01.md
---
work_package_id: "WP01"
title: "Setup database schema"
dependencies: []
---

# WP02.md
---
work_package_id: "WP02"
title: "Create API endpoints"
dependencies: ["WP01"]
---
```

**Implementation commands:**

```bash
spec-kitty implement WP01         # Branches from main
spec-kitty implement WP02 --base WP01  # Branches from WP01
```

### Scenario 2: Fan-Out Dependencies

**tasks.md structure:**

```markdown
## Phase 1
- WP01: Core authentication module

## Phase 2 (all depend on WP01)
- WP02: OAuth integration (uses auth module)
- WP03: 2FA support (uses auth module)
- WP04: Session management (uses auth module)
```

**Generated WP frontmatter:**

```yaml
# WP01.md
dependencies: []

# WP02.md, WP03.md, WP04.md
dependencies: ["WP01"]
```

**Implementation commands:**

```bash
spec-kitty implement WP01              # Branches from main

# After WP01 committed, run in parallel:
spec-kitty implement WP02 --base WP01  # Agent A
spec-kitty implement WP03 --base WP01  # Agent B (parallel)
spec-kitty implement WP04 --base WP01  # Agent C (parallel)
```

**Result**: 3 agents work simultaneously on WP02, WP03, WP04, all building on WP01's foundation.

### Scenario 3: Complex DAG

**tasks.md structure:**

```markdown
- WP01: Database schema
- WP02: API layer (depends on WP01)
- WP03: Business logic (depends on WP01)
- WP04: API endpoints (depends on WP02 and WP03)
```

**Dependency graph:**

```
    WP01
    /  \
  WP02  WP03
    \  /
    WP04
```

**Generated frontmatter:**

```yaml
# WP01.md: dependencies: []
# WP02.md: dependencies: ["WP01"]
# WP03.md: dependencies: ["WP01"]
# WP04.md: dependencies: ["WP02", "WP03"]
```

**Implementation order:**

```bash
spec-kitty implement WP01
# After WP01 done:
spec-kitty implement WP02 --base WP01  # Parallel
spec-kitty implement WP03 --base WP01  # Parallel
# After both WP02 and WP03 done:
spec-kitty implement WP04 --base WP03  # Gets WP03 + WP01, manually merge WP02
```

**Note**: WP04 depends on both WP02 and WP03, but `--base` can only specify one. Agent must manually merge the other dependency (git limitation, will be solved by jj in future).

---

## Validation Rules Summary

| Validation | When Checked | Error if Violated |
|------------|-------------|-------------------|
| No self-dependency | Tasks generation | "WP01 cannot depend on itself" |
| Dependencies exist | Tasks generation | "WP02 depends on WP99 which doesn't exist" |
| No circular deps | Tasks generation | "Circular dependency: WP01 → WP02 → WP01" |
| Base workspace exists | Implement command | "Base workspace WP01 does not exist. Implement WP01 first" |
| Valid WP ID format | Frontmatter parsing | "Invalid WP ID: WP1 (must be WP## format)" |
| No legacy worktrees | Upgrade to 0.11.0 | "Legacy worktrees detected: 009-feature. Complete or delete before upgrading" |
