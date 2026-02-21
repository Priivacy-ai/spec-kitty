# Implementation Plan: First-Class Jujutsu VCS Integration

**Branch**: `015-first-class-jujutsu-vcs-integration` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/015-first-class-jujutsu-vcs-integration/spec.md`

## Summary

Introduce jujutsu (jj) as a first-class VCS alternative to git in spec-kitty. When jj is available, it becomes the default for new features, leveraging auto-rebase and conflict-as-data for autonomous multi-agent parallel development. Git remains fully supported as fallback. Per-feature VCS selection allows mixed workflows.

**Key Technical Approach**: Hybrid abstraction - thin Protocol for core operations that differ between backends, standalone functions for backend-specific features, stateless factory function for detection/instantiation.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: subprocess (for jj/git CLI invocation), typing (Protocol), dataclasses
**Storage**: Filesystem only (YAML frontmatter, meta.json, git/jj repositories)
**Testing**: pytest with parametrized tests for abstraction parity, `@pytest.mark.jj` for jj-specific tests (skip if jj unavailable)
**Target Platform**: Cross-platform (macOS, Linux, Windows)
**Project Type**: Single CLI application (existing structure)
**Performance Goals**: VCS operations should complete in <5s for typical workspace operations
**Constraints**: No mocking of jj in tests - real execution required; backward compatibility with git-only users
**Scale/Scope**: 24 functional requirements, 9 user stories, touches ~10 source files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file exists for this project. Proceeding with standard engineering practices:

- Favor simplicity over abstraction
- Maintain backward compatibility
- Match existing codebase style (functions over classes where appropriate)

## Project Structure

### Documentation (this feature)

```
kitty-specs/015-first-class-jujutsu-vcs-integration/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output - VCS types and entities
├── checklists/          # Validation checklists
│   └── requirements.md  # Spec quality checklist (complete)
├── contracts/           # Phase 1 output - VCS Protocol definition
│   └── vcs-protocol.py  # Protocol and type definitions
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── vcs/                      # NEW: VCS abstraction package
│   │   ├── __init__.py           # Public API: get_vcs(), VCSProtocol, types
│   │   ├── protocol.py           # VCSProtocol definition
│   │   ├── types.py              # ConflictInfo, SyncResult, ChangeInfo, etc.
│   │   ├── git.py                # GitVCS implementation
│   │   ├── jujutsu.py            # JujutsuVCS implementation
│   │   └── detection.py          # Tool detection, factory function
│   ├── git_ops.py                # DEPRECATED: Migrate callers to vcs/
│   ├── worktree.py               # MODIFY: Use VCS abstraction for workspace creation
│   └── dependency_graph.py       # UNCHANGED
├── cli/
│   └── commands/
│       ├── implement.py          # MODIFY: Use VCS abstraction
│       ├── merge.py              # MODIFY: Use VCS abstraction
│       ├── init.py               # MODIFY: Add jj detection, info message
│       ├── sync.py               # NEW: spec-kitty sync command
│       └── ops.py                # NEW: spec-kitty ops log/undo commands
└── ...

tests/
├── specify_cli/
│   ├── core/
│   │   └── vcs/                  # NEW: VCS test package
│   │       ├── test_git.py       # Git-specific tests
│   │       ├── test_jujutsu.py   # jj-specific tests (@pytest.mark.jj)
│   │       ├── test_detection.py # Detection/factory tests
│   │       └── test_abstraction.py  # Parametrized parity tests
│   └── cli/
│       └── commands/
│           ├── test_sync.py      # NEW
│           └── test_ops.py       # NEW
└── conftest.py                   # Add jj_available fixture, jj marker
```

**Structure Decision**: New `vcs/` subpackage under `core/` for clean separation. Existing `git_ops.py` deprecated but kept for gradual migration. All VCS-dependent code updated to use the abstraction.

## Architecture Decisions

### Decision 1: Hybrid Abstraction Approach

**Choice**: Thin Protocol + standalone functions + stateless factory

**Rationale**:

- Protocol for operations that truly differ (workspace creation, sync, conflict detection)
- Standalone functions for backend-specific features (jj ops log has no git equivalent)
- Factory function (not class) for stateless detection/instantiation
- Matches spec-kitty's existing functional style

**Alternatives Rejected**:

- Full Protocol-based: No home for shared behavior, runtime enforcement issues
- Strategy/Factory pattern: Over-engineered for the use case, state management complexity

### Decision 2: Module Organization

**Choice**: New `src/specify_cli/core/vcs/` subpackage

**Rationale**:

- Clean separation of VCS concerns
- Room to grow (additional backends, utilities)
- Clear public API via `__init__.py`

**Alternatives Rejected**:

- Flat files alongside `git_ops.py`: Cramped, harder to navigate

### Decision 3: Testing Strategy

**Choice**: Parametrized tests + `@pytest.mark.jj` marker

**Rationale**:

- Parametrized tests prove abstraction works identically for both backends
- `@pytest.mark.jj` allows skipping jj tests when jj unavailable
- No mocking - real VCS execution required (per spec)

**Implementation**:

```python
# conftest.py
import shutil
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "jj: tests requiring jujutsu")

@pytest.fixture
def jj_available():
    return shutil.which("jj") is not None

# test_abstraction.py
@pytest.mark.parametrize("backend", [
    "git",
    pytest.param("jj", marks=pytest.mark.jj)
])
def test_workspace_creation(backend, tmp_path):
    ...
```

### Decision 4: Rich Automation Data Model

**Choice**: `SyncResult` includes `changes_integrated` with commit details

**Rationale**:

- Sailing towards full automation - agents need to understand what changed
- Change IDs (jj) provide stable identity across rebases
- Commit messages help agents make informed decisions

**Data Structures** (see data-model.md for complete definitions):

- `ConflictInfo`: File path, type, line ranges, sides, resolution status
- `SyncResult`: Status, conflicts, files updated, changes integrated
- `ChangeInfo`: Change ID (jj) or commit SHA (git), message, author, timestamp

### Decision 5: Colocated Mode Default

**Choice**: When both jj and git are installed, use colocated mode (both `.jj/` and `.git/`)

**Rationale**:

- Preserves git compatibility for CI/CD, GitHub, team members
- jj automatically syncs with git on each command
- Gradual adoption without breaking existing workflows

**Implementation**:

- `jj git init --colocate` for new features with jj
- Detection in factory: check for both tools, configure accordingly

## Migration Strategy

### Phase 1: Abstraction Layer (Non-Breaking)

1. Create `vcs/` package with Protocol and implementations
2. Implement `GitVCS` wrapping existing `git_ops.py` functions
3. Implement `JujutsuVCS` with jj CLI calls
4. Add factory function with detection logic
5. All new code uses abstraction; existing code unchanged

### Phase 2: Command Updates

1. Update `implement.py` to use VCS abstraction for workspace creation
2. Update `merge.py` to use VCS abstraction
3. Update `init.py` to detect jj, show recommendation message
4. Add new `sync` and `ops` commands

### Phase 3: Deprecation

1. Mark `git_ops.py` functions as deprecated
2. Update remaining callers to use `vcs/` package
3. Eventually remove `git_ops.py` (future version)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| jj CLI changes break integration | Pin minimum jj version (0.20+), test against CI with specific version |
| Colocated mode sync issues | Test edge cases thoroughly, provide `--vcs=git` escape hatch |
| Performance regression | Benchmark workspace creation/sync before and after |
| Breaking existing git users | All changes backward compatible, git remains default if jj unavailable |

## Dependencies

**External**:

- jj (jujutsu) CLI tool - optional, enhances functionality when available
- git CLI tool - required fallback

**Internal** (files to modify):

- `src/specify_cli/core/worktree.py` - workspace creation
- `src/specify_cli/cli/commands/implement.py` - implement command
- `src/specify_cli/cli/commands/merge.py` - merge command
- `src/specify_cli/cli/commands/init.py` - initialization + jj detection

## Deferred to Future Features

- **Dashboard conflict indicators**: Visual workspace state (clean/stale/conflicted) in web dashboard
- **Automatic conflict resolution hints**: AI-assisted conflict resolution suggestions
- **jj-specific advanced features**: Full revset support, operation log visualization
