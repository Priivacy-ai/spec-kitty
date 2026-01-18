# Implementation Plan: Smarter Feature Merge with Pre-flight and Auto-cleanup

**Branch**: `017-smarter-feature-merge-with-preflight` | **Date**: 2025-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md`

## Summary

Enhance the `spec-kitty merge` command to provide pre-flight validation, conflict forecasting, dependency-ordered merging, automatic status file conflict resolution, and resume capability. The current ~590-line `merge.py` will be refactored into a modular architecture with dedicated components for each capability.

**Key Technical Decisions**:
- **Status file resolution**: Post-merge Python cleanup (not git merge drivers) - detects conflict markers in status files and resolves them before committing
- **Merge state persistence**: JSON file at `.kittify/merge-state.json`
- **Architecture**: Extract merge logic into `src/specify_cli/merge/` subpackage

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (frontmatter parsing), pathlib (file operations)
**Storage**: Filesystem only (`.kittify/merge-state.json` for state persistence)
**Testing**: pytest with existing test infrastructure
**Target Platform**: macOS, Linux (CLI tool)
**Project Type**: Single Python package (existing structure)
**Performance Goals**: Handle features with 10+ WPs without noticeable delay
**Constraints**: Must work with existing git installations (no custom merge drivers required)
**Scale/Scope**: Features with up to 20 WPs, repositories of any size

## Constitution Check

*No constitution file exists. Proceeding with standard Python best practices.*

- Follow existing code patterns in `src/specify_cli/`
- Use existing utilities: `dependency_graph.py`, `git_ops.py`, `frontmatter.py`
- Maintain backward compatibility with existing `--dry-run`, `--keep-branch`, etc. flags
- Add new flags additively (no breaking changes to CLI interface)

## Project Structure

### Documentation (this feature)

```
kitty-specs/017-smarter-feature-merge-with-preflight/
├── spec.md              # Feature specification
├── plan.md              # This file
├── data-model.md        # Merge state and conflict forecast entities
├── quickstart.md        # Quick reference for new merge features
└── tasks/               # Work package files (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/
│   └── commands/
│       └── merge.py           # MODIFY: Slim down, delegate to merge/ subpackage
├── merge/                     # NEW: Merge subpackage
│   ├── __init__.py           # Public API exports
│   ├── preflight.py          # Pre-flight validation checks
│   ├── forecast.py           # Conflict prediction
│   ├── ordering.py           # Topological sort, merge order
│   ├── status_resolver.py    # Status file auto-resolution
│   ├── state.py              # Merge state persistence/resume
│   └── executor.py           # Core merge execution logic
├── core/
│   └── dependency_graph.py    # MODIFY: Add topological_sort()
└── ...

tests/
├── specify_cli/
│   ├── test_merge/            # NEW: Test directory for merge subpackage
│   │   ├── test_preflight.py
│   │   ├── test_forecast.py
│   │   ├── test_ordering.py
│   │   ├── test_status_resolver.py
│   │   └── test_state.py
│   └── test_cli/
│       └── test_merge_workspace_per_wp.py  # MODIFY: Add integration tests
└── ...
```

**Structure Decision**: Create new `src/specify_cli/merge/` subpackage to modularize the merge logic. This keeps `merge.py` as a thin CLI wrapper while allowing unit testing of individual components.

## Component Design

### 1. Pre-flight Validation (`merge/preflight.py`)

```python
@dataclass
class PreflightResult:
    passed: bool
    wp_statuses: list[WPStatus]  # (wp_id, path, clean: bool, error: str | None)
    target_diverged: bool
    target_divergence_msg: str | None
    errors: list[str]
    warnings: list[str]

def run_preflight(
    feature_slug: str,
    target_branch: str,
    repo_root: Path,
) -> PreflightResult:
    """Check all WPs and target branch before merge."""
```

**Responsibilities**:
- FR-001: Check all WP worktrees for uncommitted changes
- FR-002: Verify target branch can fast-forward to origin
- FR-003: Collect all issues into single result object
- FR-004: Return result without modifying any branches

### 2. Conflict Forecast (`merge/forecast.py`)

```python
@dataclass
class ConflictPrediction:
    file_path: str
    conflicting_wps: list[str]  # WP IDs that touch this file
    confidence: str  # "certain", "likely", "possible"

def predict_conflicts(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    repo_root: Path,
) -> list[ConflictPrediction]:
    """Predict which files will conflict based on git diff analysis."""
```

**Responsibilities**:
- FR-005: Compare each WP's changes against target and other WPs
- FR-006: Group conflicts by file path
- FR-007: Return in merge order

**Algorithm**:
1. For each WP, run `git diff --name-only <target>...<wp_branch>` to get modified files
2. Build file → [WPs] mapping
3. Files touched by 2+ WPs are conflict candidates
4. Run `git merge-tree` for definite conflict detection (git 2.38+)

### 3. Merge Ordering (`merge/ordering.py`)

```python
def get_merge_order(
    wp_workspaces: list[tuple[Path, str, str]],
    feature_dir: Path,
) -> list[tuple[Path, str, str]]:
    """Return WPs in dependency order (topological sort)."""
```

**Responsibilities**:
- FR-008: Parse dependencies from WP frontmatter (reuse `dependency_graph.py`)
- FR-009: Topological sort
- FR-010: Detect and report cycles
- FR-011: Fall back to numerical order if no dependencies

**Implementation**: Add `topological_sort()` to `core/dependency_graph.py`:
```python
def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm for topological ordering."""
```

### 4. Status File Resolver (`merge/status_resolver.py`)

```python
@dataclass
class ResolutionResult:
    file_path: Path
    resolved: bool
    resolution_type: str  # "lane", "checkbox", "history", "manual_required"
    original_conflicts: int
    resolved_conflicts: int

def resolve_status_conflicts(repo_root: Path) -> list[ResolutionResult]:
    """Auto-resolve conflicts in status files after merge."""
```

**Responsibilities**:
- FR-012: Only process files matching `kitty-specs/**/tasks/*.md` or `kitty-specs/**/tasks.md`
- FR-013: Resolve `lane:` by "more done" value (done > for_review > doing > planned)
- FR-014: Resolve checkboxes by preferring `[x]`
- FR-015: Resolve `history:` by chronological concatenation
- FR-016: Leave non-status files untouched

**Algorithm**:
1. After each WP merge, check `git diff --name-only --diff-filter=U` for conflicted files
2. For each conflicted file matching status patterns:
   a. Parse conflict markers
   b. Apply resolution rules based on content type
   c. Write resolved content
   d. `git add` the file
3. If all conflicts resolved, proceed; else pause for manual resolution

### 5. Merge State (`merge/state.py`)

```python
@dataclass
class MergeState:
    feature_slug: str
    target_branch: str
    wp_order: list[str]  # WP IDs in merge order
    completed_wps: list[str]
    current_wp: str | None
    has_pending_conflicts: bool
    started_at: str  # ISO timestamp
    last_updated: str

def save_state(state: MergeState, repo_root: Path) -> None:
    """Persist to .kittify/merge-state.json"""

def load_state(repo_root: Path) -> MergeState | None:
    """Load existing state or None if no merge in progress"""

def clear_state(repo_root: Path) -> None:
    """Remove state file after completion or abort"""
```

**Responsibilities**:
- FR-021: Persist state during multi-WP merge
- FR-022: Support `--resume` flag
- FR-023: Clear on success or explicit abort
- FR-024: Detect active git merge state

### 6. Merge Executor (`merge/executor.py`)

```python
def execute_merge(
    feature_slug: str,
    target_branch: str,
    wp_workspaces: list[tuple[Path, str, str]],
    strategy: str,
    repo_root: Path,
    state: MergeState,
    tracker: StepTracker,
) -> bool:
    """Execute merge for all WPs with state tracking."""
```

**Responsibilities**:
- Orchestrate preflight, ordering, merge, resolution, cleanup
- Update state after each WP
- Handle interruptions gracefully

## CLI Changes

Update `merge.py` to add new flags:

```python
def merge(
    # Existing flags (unchanged)
    strategy: str = typer.Option("merge", ...),
    delete_branch: bool = typer.Option(True, ...),
    remove_worktree: bool = typer.Option(True, ...),
    push: bool = typer.Option(False, ...),
    target_branch: str = typer.Option("main", ...),
    dry_run: bool = typer.Option(False, ...),

    # New flags
    resume: bool = typer.Option(False, "--resume", help="Resume interrupted merge"),
    single: bool = typer.Option(False, "--single", help="Merge only current WP (legacy behavior)"),
    feature: str = typer.Option(None, "--feature", help="Feature slug (when running from main)"),
) -> None:
```

## Complexity Tracking

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| New subpackage | `merge/` with 6 modules | Existing `merge.py` is 590 lines; modularization enables unit testing and clearer separation |
| State persistence | JSON file | Simple, human-readable, no new dependencies |
| Conflict forecast | `git merge-tree` + diff analysis | Git-native approach, no custom algorithms needed |
| Status resolution | Post-merge Python | Non-invasive, works without git configuration |

## Dependencies on Existing Code

| Module | Usage |
|--------|-------|
| `core/dependency_graph.py` | Reuse `build_dependency_graph()`, `detect_cycles()`, add `topological_sort()` |
| `core/git_ops.py` | Reuse `run_command()` for git operations |
| `frontmatter.py` | Reuse `read_frontmatter()` for WP dependency parsing |
| `cli/helpers.py` | Reuse `console`, `StepTracker`, `show_banner()` |
| `tasks_support.py` | Reuse `find_repo_root()`, `TaskCliError` |

## Test Strategy

| Component | Test Type | Key Scenarios |
|-----------|-----------|---------------|
| `preflight.py` | Unit | Clean worktrees, dirty worktrees, diverged target, mixed states |
| `forecast.py` | Unit | No conflicts, single conflict, multi-WP conflict, status file detection |
| `ordering.py` | Unit | Linear chain, fan-out, diamond, cycles, no dependencies |
| `status_resolver.py` | Unit | Lane conflicts, checkbox conflicts, history merge, non-status files |
| `state.py` | Unit | Save/load/clear, resume from various points |
| Integration | Integration | Full merge flow, interrupted merge, resume, cleanup |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| git merge-tree not available (< 2.38) | Fall back to diff-based heuristic with "possible" confidence |
| Status resolution misidentifies content | Strict pattern matching on frontmatter YAML structure |
| State file corruption | Validate JSON on load, clear and restart if invalid |
| Cleanup fails mid-merge | Continue with remaining cleanup, report failures at end |

## Non-Goals (Confirmed Out of Scope)

- JJ-specific merge strategies
- SQLite or external status storage
- Auto-rebase of remaining worktrees
- Octopus merge for independent WPs
- External merge tool integration
