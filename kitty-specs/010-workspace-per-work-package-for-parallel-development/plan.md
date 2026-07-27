# Implementation Plan: Workspace-per-Work-Package for Parallel Development

**Branch**: `010-workspace-per-work-package-for-parallel-development` | **Date**: 2026-01-07 | **Spec**: [spec.md](spec.md)

## Summary

Transform Spec Kitty's workspace model from "one worktree per feature" to "one worktree per work package" to enable parallel multi-agent development. This breaking change (0.10.12 → 0.11.0) introduces:

1. **Planning artifacts in main**: `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks` work in main repository, committing directly to `main` branch (no worktree created)
2. **On-demand WP workspaces**: `spec-kitty implement WP##` creates `.worktrees/###-feature-WP##/` branching from main or specified base
3. **Dependency tracking**: WP frontmatter includes `dependencies: ["WP01"]` field, parsed by Python utilities for validation and cycle detection
4. **Breaking upgrade**: Pre-upgrade validation blocks if legacy worktrees exist, providing cleanup tools (merge or delete)

**Technical Approach**: Test-driven development ensures all 12 agent templates updated exhaustively, with zero legacy code in 0.11.0 codebase.

## Technical Context

**Language/Version**: Python 3.11+ (existing Spec Kitty requirement)

**Primary Dependencies**:
- `typer` - CLI command framework (existing)
- `rich` - Console output formatting (existing)
- `ruamel.yaml` - YAML frontmatter parsing (existing)
- `pathlib` - Path operations (stdlib)
- `subprocess` - Git worktree operations (stdlib)
- `pytest` - Testing framework (existing)

**Storage**: Filesystem only (YAML frontmatter in markdown files, git repositories)

**Testing**:
- **Unit tests**: Dependency graph utilities (parsing, cycle detection, validation)
- **Integration tests**: Full workflow (specify → plan → tasks → implement with dependencies)
- **Migration tests**: Verify all 12 agent templates updated (parametrized across agents)

**Target Platform**: Cross-platform (macOS, Linux, Windows) - Python 3.11+ environments

**Project Type**: Single project (Spec Kitty CLI tool)

**Performance Goals**:
- Dependency parsing: <100ms for 50 WPs
- Cycle detection: <500ms for complex graphs (50 nodes, 100 edges)
- Worktree creation: <2 seconds per WP workspace

**Constraints**:
- **Git compatibility**: Must work with git 2.5.0+ (when `git worktree` was introduced)
- **Backward incompatibility accepted**: Version 0.11.0 is breaking change, no legacy support
- **File-based state**: All dependency data in WP frontmatter (no database)
- **Test-first mandate**: Migration tests written before implementation to prevent gaps

**Scale/Scope**:
- Support features with up to 50 work packages
- Handle dependency graphs with complex fan-out (e.g., 10 WPs depending on WP01)
- 12 AI agent templates to update (Claude, Copilot, Gemini, Cursor, Qwen, OpenCode, Windsurf, Codex, Kilocode, Augment, Roo, Amazon Q)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Jujutsu-First VCS Philosophy

**Alignment**: ✅ **COMPATIBLE**

This feature uses Git worktrees exclusively (no jj yet), but is designed as foundation for future jj workspace integration. The workspace-per-WP model maps cleanly to jj workspaces, making future jj integration straightforward.

**Rationale**: Implementing workspace-per-WP with Git first validates the architectural model before adding jj complexity. Future jj integration will swap `git worktree add` for `jj workspace add` without changing the fundamental model.

### II. Multi-Agent Orchestration

**Alignment**: ✅ **STRONGLY ALIGNED**

This feature directly enables the constitutional goal of "multiple AI agents working together on a single codebase" by providing isolated workspaces for parallel work.

**Evidence**:
- FR-001 through FR-003: All 12 agents get updated templates
- User Story 1: Parallel multi-agent development is the primary capability
- Spec section: "Agent coordination is external" - this feature provides technical isolation, agents coordinate which WP to implement

### III. Specification-Driven Development

**Alignment**: ✅ **COMPLIANT**

This feature follows the constitutional workflow: Specify → Plan → Tasks → Implement.

**Breaking Change Impact**: Planning workflow changes (specify/plan/tasks now in main), but the sequence and gates remain intact. Each phase still produces version-controlled artifacts before proceeding.

### IV. Work Package Granularity

**Alignment**: ✅ **FOUNDATIONAL ENHANCEMENT**

This feature makes WPs "independently testable, reviewable, and mergeable" a reality by giving each WP its own isolated workspace.

**Enhancement**: Adds `dependencies: []` field to WP frontmatter, making dependency relationships explicit and parseable (constitutional principle: "Frontmatter State").

### V. File-Based Everything (No Database)

**Alignment**: ✅ **COMPLIANT**

All new state stored in files:
- Dependencies: WP frontmatter (`dependencies: ["WP01"]`)
- Workspace paths: Filesystem (`.worktrees/###-feature-WP##/`)
- Planning artifacts: Main repository (`kitty-specs/###-feature/`)

**No external services or databases introduced.**

### Constitutional Compliance Summary

**Result**: ✅ **PASS** - All 5 constitutional principles satisfied.

**Note**: Breaking change justified under Governance principle: "Breaking Changes: Must be justified against constitutional goals and include migration path"
- Justification: Enables Multi-Agent Orchestration (Principle II) and Work Package Granularity (Principle IV)
- Migration path: Pre-upgrade validation + cleanup tools provided

## Project Structure

### Documentation (this feature)

```
kitty-specs/010-workspace-per-work-package-for-parallel-development/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (Phase 1 output)
├── data-model.md        # Dependency graph entities (Phase 1 output)
├── checklists/
│   └── requirements.md  # Spec validation (completed)
└── research/            # Research findings (if needed)
```

### Source Code (Spec Kitty repository structure)

```
src/specify_cli/
├── core/
│   ├── git_ops.py              # MODIFY: Add worktree creation for WP workspaces
│   ├── worktree.py             # MODIFY: Update to workspace-per-WP model
│   ├── dependency_graph.py     # NEW: Dependency parsing, cycle detection, validation
│   └── paths.py                # Existing (no changes)
│
├── cli/commands/
│   ├── agent/
│   │   ├── feature.py          # MODIFY: Remove worktree creation from create-feature
│   │   └── tasks.py            # MODIFY: Generate dependencies in WP frontmatter
│   ├── init.py                 # NO CHANGE (project initialization)
│   ├── merge.py                # MODIFY: Handle workspace-per-WP merge (all WPs)
│   └── implement.py            # NEW: spec-kitty implement WP## [--base WP##]
│
├── upgrade/
│   ├── metadata.py             # MODIFY: Track version for 0.11.0 upgrade validation
│   └── migrations/
│       └── m_0_11_0_workspace_per_wp.py  # NEW: Pre-upgrade validation, agent template updates
│
└── frontmatter.py              # MODIFY: Add dependencies field to WP schema

tests/specify_cli/
├── test_dependency_graph.py           # NEW: Unit tests for dependency utilities
├── test_workspace_per_wp_migration.py # NEW: Migration test (all 12 agents updated)
└── test_integration/
    └── test_workspace_per_wp_workflow.py  # NEW: Full workflow (specify → implement)

.claude/commands/            # MODIFY: Update specify.md, plan.md, tasks.md, implement.md
.github/prompts/             # MODIFY: Update specify.md, plan.md, tasks.md, implement.md
.gemini/commands/            # MODIFY: (same)
.cursor/commands/            # MODIFY: (same)
.qwen/commands/              # MODIFY: (same)
.opencode/command/           # MODIFY: (same)
.windsurf/workflows/         # MODIFY: (same)
.codex/prompts/              # MODIFY: (same)
.kilocode/workflows/         # MODIFY: (same)
.augment/commands/           # MODIFY: (same)
.roo/commands/               # MODIFY: (same)
.amazonq/prompts/            # MODIFY: (same)
```

**Structure Decision**: Single project structure (Spec Kitty CLI tool). Core changes in `src/specify_cli/core/` (dependency graph utilities, worktree management), CLI changes in `src/specify_cli/cli/commands/` (implement command, tasks generation), and exhaustive template updates across all 12 agent directories.

## Complexity Tracking

*No constitutional violations requiring justification*

This feature adds complexity (dependency graph, workspace-per-WP model, breaking upgrade) but all complexity is justified by constitutional goals (Multi-Agent Orchestration, Work Package Granularity).

---

## Phase 0: Research & Discovery

### Research Questions

**Q1: Git worktree best practices for dependency chains**
- **Status**: No research needed
- **Reason**: Git worktree branching model is well-understood. WP02 branches from WP01's branch via `git worktree add .worktrees/010-feature-WP02 -b 010-feature-WP02 010-feature-WP01` (standard git operation).

**Q2: Cycle detection algorithms for dependency graphs**
- **Status**: Use standard algorithms
- **Decision**: Depth-first search (DFS) with visited/recursion stack for cycle detection. O(V+E) complexity, sufficient for <50 WPs.
- **Alternatives considered**: Topological sort (also O(V+E), but we only need cycle detection, not ordering)

**Q3: WP frontmatter schema for dependencies**
- **Status**: Decided during planning
- **Decision**: `dependencies: ["WP01", "WP02"]` - list of WP IDs
- **Rationale**: Parseable YAML, extends existing frontmatter pattern, self-documenting

**Q4: Migration strategy for breaking changes**
- **Status**: Decided during planning
- **Decision**: Semver bump to 0.11.0, pre-upgrade validation blocks if legacy worktrees exist
- **Rationale**: Zero legacy code in 0.11.0, clean break, users complete or delete in-progress features before upgrading

### Research Output

No `research.md` file needed - all decisions resolved during planning interrogation and documented above.

---

## Phase 1: Design & Architecture

### 1.1 Dependency Graph Data Model

See [data-model.md](data-model.md) for complete entity definitions.

**Key Entities:**
- **WorkPackage**: Represents a WP with dependencies field
- **DependencyGraph**: Represents relationships between WPs
- **Worktree**: Represents a git worktree for a WP

### 1.2 Command Design

#### `spec-kitty implement WP## [--base WPXX]`

**NEW COMMAND** - Creates workspace for work package implementation

**Behavior:**
```bash
# WP01 (no dependencies)
spec-kitty implement WP01
→ Creates .worktrees/010-feature-WP01/
→ Branches from main
→ Contains planning artifacts from main

# WP02 (depends on WP01)
spec-kitty implement WP02 --base WP01
→ Creates .worktrees/010-feature-WP02/
→ Branches from branch 010-feature-WP01
→ Contains planning artifacts + WP01's code changes

# Error case: base doesn't exist
spec-kitty implement WP02 --base WP01
→ ERROR: "Base workspace WP01 does not exist. Implement WP01 first"
```

**Validation:**
1. Check WP frontmatter has `work_package_id: WP##`
2. If `--base` provided, verify base workspace exists (`.worktrees/###-feature-WPXX/`)
3. If WP has dependencies in frontmatter but no `--base` provided, error with suggestion
4. If workspace already exists, check if valid worktree (reuse if yes, error if no)

#### Modified Commands

**`/spec-kitty.specify`**:
- **OLD**: Created `.worktrees/###-feature/` worktree
- **NEW**: Creates `kitty-specs/###-feature/spec.md` in main repo, commits to main, NO worktree

**`/spec-kitty.plan`**:
- **OLD**: Worked in `.worktrees/###-feature/` worktree
- **NEW**: Works in main repo, commits plan.md to main, NO worktree

**`/spec-kitty.tasks`**:
- **OLD**: Created tasks.md in `.worktrees/###-feature/` worktree
- **NEW**: Creates tasks/*.md in main repo, commits to main, parses dependencies and writes to WP frontmatter

**`spec-kitty merge ###-feature`**:
- **OLD**: Merged single feature branch
- **NEW**: Validates all WP worktrees merged/cleaned, merges feature as before (all WPs as one merge for now)

### 1.3 Dependency Graph Utilities

**Module**: `src/specify_cli/core/dependency_graph.py`

**Functions:**
```python
def parse_wp_dependencies(wp_file: Path) -> list[str]:
    """Parse dependencies from WP frontmatter."""
    # Read YAML frontmatter
    # Return dependencies list (e.g., ["WP01", "WP02"])

def build_dependency_graph(feature_dir: Path) -> dict[str, list[str]]:
    """Build dependency graph from all WPs in feature."""
    # Scan tasks/*.md files
    # Parse each WP's dependencies
    # Return adjacency list: {"WP01": [], "WP02": ["WP01"], ...}

def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]] | None:
    """Detect circular dependencies using DFS."""
    # Returns list of cycles if found, None otherwise
    # Each cycle is list of WP IDs forming the circle

def validate_dependencies(
    wp_id: str,
    declared_deps: list[str],
    graph: dict[str, list[str]]
) -> tuple[bool, list[str]]:
    """Validate that WP's dependencies exist and are valid."""
    # Returns (is_valid, error_messages)
    # Checks: deps exist, no self-dependency, no cycles

def get_dependents(wp_id: str, graph: dict[str, list[str]]) -> list[str]:
    """Get list of WPs that depend on this WP."""
    # Used for review feedback warnings
    # Returns ["WP02", "WP03"] if they depend on wp_id
```

**Testing Strategy**: TDD - write tests first in `tests/specify_cli/test_dependency_graph.py`:
- Test cycle detection with various graph shapes (no cycles, simple cycle, complex cycle)
- Test dependency validation (missing deps, self-deps, invalid WP IDs)
- Test dependent lookup for warnings

### 1.4 Migration Design

**Migration**: `m_0_11_0_workspace_per_wp.py`

**Pre-upgrade validation:**
```python
def validate_upgrade() -> tuple[bool, list[str]]:
    """Check if project ready for 0.11.0 upgrade."""
    # 1. Scan .worktrees/ for legacy worktrees (###-feature pattern)
    # 2. If found, return (False, ["Legacy worktrees detected: 009-jj-vcs"])
    # 3. Suggest: "Complete or delete features before upgrading: spec-kitty merge 009-jj-vcs OR git worktree remove ..."
    # 4. If clean, return (True, [])
```

**Agent template updates:**
```python
def update_agent_templates():
    """Update all 12 agent directories with new workflow."""
    AGENT_DIRS = [
        ".claude/commands/",
        ".github/prompts/",
        ".gemini/commands/",
        # ... (all 12)
    ]
    for agent_dir in AGENT_DIRS:
        update_specify_template(agent_dir)  # Remove worktree creation
        update_plan_template(agent_dir)     # Remove worktree reference
        update_tasks_template(agent_dir)    # Add dependency generation
        add_implement_template(agent_dir)   # New command template
```

**Test coverage**: `tests/specify_cli/test_workspace_per_wp_migration.py`
```python
@pytest.mark.parametrize("agent_dir", AGENT_DIRS)
def test_agent_template_updated(agent_dir):
    """Verify each agent has updated templates."""
    # Check specify.md no longer creates worktree
    # Check tasks.md generates dependencies
    # Check implement.md exists with --base flag docs
```

### 1.5 WP Frontmatter Schema Extension

**Current schema** (in `src/specify_cli/frontmatter.py`):
```yaml
---
work_package_id: "WP01"
title: "Setup Infrastructure"
lane: "planned"
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
---
```

**Extended schema** (0.11.0):
```yaml
---
work_package_id: "WP01"
title: "Setup Infrastructure"
lane: "planned"
dependencies: []              # NEW: List of WP IDs this WP depends on
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
---
```

**Validation rules**:
- `dependencies` field is optional (defaults to `[]`)
- Each dependency must be valid WP ID format (`WP##`)
- Dependencies must exist in same feature
- No self-dependencies (`WP01` cannot depend on `WP01`)
- No circular dependencies (validated during tasks generation)

### 1.6 Workflow Changes

**Planning workflow (NO worktree)**:
```
User in main repo
↓
/spec-kitty.specify
  → Creates kitty-specs/010-feature/spec.md
  → Commits to main
  → NO WORKTREE CREATED
↓
/spec-kitty.plan
  → Creates kitty-specs/010-feature/plan.md
  → Commits to main
  → NO WORKTREE CREATED
↓
/spec-kitty.tasks
  → Parses tasks.md for dependencies
  → Creates kitty-specs/010-feature/tasks/WP01.md, WP02.md, WP03.md
  → Writes dependencies: [] to each WP frontmatter
  → Commits to main
  → NO WORKTREE CREATED
```

**Implementation workflow (ON-DEMAND worktrees)**:
```
Agent A:
  spec-kitty implement WP01
  → Creates .worktrees/010-feature-WP01/
  → Branches from main (has spec, plan, tasks)
  → Works in isolated directory

Agent B (parallel):
  spec-kitty implement WP03
  → Creates .worktrees/010-feature-WP03/
  → Branches from main (independent WP)
  → Works in isolated directory

Agent C (dependent):
  spec-kitty implement WP02 --base WP01
  → Creates .worktrees/010-feature-WP02/
  → Branches from 010-feature-WP01 branch
  → Gets WP01's code changes
```

**Merge workflow (UNCHANGED for now)**:
```
spec-kitty merge 010-feature
  → Validates all WP worktrees merged or removed
  → Merges entire feature to main (all WPs as one merge)
  → Note: Per-WP incremental merging deferred to future version
```

---

## Phase 1 Deliverables

1. **data-model.md** - Entity definitions for dependency graph, worktree, work package
2. **quickstart.md** - Quick reference for new workspace-per-WP workflow
3. **Agent context update** - Run agent script to update CLAUDE.md with new workflow details

---

## Implementation Notes

### Test-Driven Development Approach

**Order of implementation (TDD):**

1. **Write migration tests FIRST** (`test_workspace_per_wp_migration.py`)
   - Test that all 12 agent templates are updated
   - Test runs, currently FAILS (templates not yet updated)

2. **Write dependency graph tests** (`test_dependency_graph.py`)
   - Test cycle detection, validation, parsing
   - Tests run, currently FAIL (module doesn't exist)

3. **Implement to make tests pass**:
   - Create `dependency_graph.py` module
   - Create migration `m_0_11_0_workspace_per_wp.py`
   - Update all 12 agent templates
   - Modify commands (implement, tasks, merge)

4. **Write integration tests** (`test_workspace_per_wp_workflow.py`)
   - Test full workflow: specify → plan → tasks → implement
   - Test dependency handling
   - Tests run, verify end-to-end behavior

### Breaking Change Communication

**Version 0.11.0 release notes MUST include:**
- ⚠️ **BREAKING CHANGE**: Workspace model changed to workspace-per-WP
- **Action required**: Complete or delete in-progress features before upgrading
- **How to prepare**: Run `spec-kitty list-legacy-features`, then merge or remove
- **What changes**: Planning commands no longer create worktrees, `spec-kitty implement` creates per-WP workspaces
- **Migration guide**: Link to docs with step-by-step upgrade process

### Rollback Plan

**If 0.11.0 upgrade causes issues:**
- Downgrade to 0.10.12: `pip install spec-kitty-cli==0.10.12`
- Note: Any features planned in 0.11.0 will need re-planning in 0.10.12 (planning artifacts in main vs worktree)
- Recommendation: Test 0.11.0 in non-production project first

---

## Next Steps

**After plan approval:**
1. Run `/spec-kitty.tasks` to generate work packages
2. Implement in test-driven order (tests first, then code)
3. Validate with real project (dogfood on Spec Kitty itself)
4. Document migration guide before release

**Post-implementation:**
- Version 0.11.0 release with breaking change notes
- Maintain 0.10.x for 6 months with critical bug fixes
- Monitor adoption, provide migration support
- After 6 months, deprecate 0.10.x

---

## Appendix: Design Decisions Log

**D1: Why frontmatter for dependencies?**
- Extends existing WP frontmatter pattern
- Parseable with ruamel.yaml (already in use)
- Self-documenting (each WP declares dependencies)
- Canonical source of truth (not in tasks.md prose)

**D2: Why not incremental WP merging in 0.11.0?**
- Adds significant complexity (merge orchestration, dependency ordering)
- Current merge workflow works (merge entire feature)
- Can be added in future version after workspace-per-WP validated
- Spec explicitly defers to future: "Out of Scope: Incremental WP-by-WP merging"

**D3: Why block upgrade instead of auto-migrate legacy worktrees?**
- Safety: Auto-migration could break in-progress work
- Simplicity: Zero legacy code in 0.11.0 codebase
- User control: Users decide how to handle in-progress features (merge or delete)
- Semantic versioning: Breaking change justified by version bump

**D4: Why TDD for migration?**
- Prevents gaps (bash→python migration left template holes)
- Ensures exhaustive coverage (all 12 agents updated)
- Regression safety (tests prevent future breakage)
- User requirement: "Lead by testing on this!"
