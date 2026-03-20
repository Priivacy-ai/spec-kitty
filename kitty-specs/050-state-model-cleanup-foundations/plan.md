# Implementation Plan: State Model Cleanup Foundations

**Branch**: `2.x` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/050-state-model-cleanup-foundations/spec.md`

## Summary

Create a machine-readable state contract (`src/specify_cli/state_contract.py`) that classifies every durable CLI state surface by root, authority, format, and Git policy. Align `.gitignore` and `GitignoreManager` with the contract for unambiguous runtime state. Add a new top-level `spec-kitty doctor` command group with a `state-roots` subcommand that displays root paths, surface classification, on-disk presence, and warnings for unsafe runtime files. Include a migration for existing projects and tests that prevent contract-gitignore drift.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich (already in project), dataclasses (stdlib)
**Storage**: Filesystem only (no database changes)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: macOS/Linux CLI
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: Doctor command completes in < 2s for a project with 20 features
**Constraints**: Zero new runtime dependencies. Data-first contract module — no side effects at import time.

## Constitution Check

*No constitution violations. This feature adds a new module and command; it does not modify existing paradigms, directives, or tool boundaries. Governance template set: software-dev-default.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/050-state-model-cleanup-foundations/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```
src/specify_cli/
├── state_contract.py              # NEW: Typed state surface registry
├── gitignore_manager.py           # MODIFIED: Derive RUNTIME_PROTECTED_ENTRIES from contract
├── cli/
│   └── commands/
│       ├── __init__.py            # MODIFIED: Register doctor command group
│       └── doctor.py              # NEW: Top-level doctor command group
├── state/                         # NEW: State diagnostics package
│   ├── __init__.py
│   └── doctor.py                  # NEW: state-roots check logic
└── runtime/
    └── home.py                    # READ ONLY: get_kittify_home() reused

src/specify_cli/upgrade/migrations/
└── m_2_0_9_state_gitignore.py     # NEW: Migration for runtime gitignore entries

tests/specify_cli/
├── test_state_contract.py         # NEW: Contract registry tests
├── test_state_doctor.py           # NEW: Doctor state-roots tests
├── test_gitignore_contract.py     # NEW: Contract↔gitignore alignment tests
└── test_state_gitignore_migration.py  # NEW: Migration tests
```

**Structure Decision**: All new code lives within the existing `src/specify_cli/` package. The new `state/` subpackage is the home for state-model diagnostics, separate from the existing `status/` subpackage (which is feature-scoped). The `state_contract.py` module lives at the package root since it is a cross-cutting manifest, not part of any single subpackage.

## Design Decisions

### D1: Doctor command placement — new top-level group

The existing `spec-kitty agent status doctor` is feature-scoped (status events, stale claims, drift). State-roots diagnostics are project-scoped. A new top-level `spec-kitty doctor` command group:
- Separates concerns (project health vs. feature health)
- Provides a natural home for future doctor checks (credential health, queue state)
- Avoids overloading the `agent status` subcommand

Implementation: `src/specify_cli/cli/commands/doctor.py` creates a `typer.Typer(name="doctor")` group. The first subcommand is `state-roots`. Registration via `app.add_typer(doctor_module.app, name="doctor")` in `__init__.py`.

### D2: State contract format — Python dataclasses + enums

Per user direction: frozen dataclasses, enums for classification, one declarative registry tuple. Data-first — reads like a typed manifest, not a service layer. `to_dict()` on `StateSurface` enables JSON export for tooling.

### D3: GitignoreManager derivation

`RUNTIME_PROTECTED_ENTRIES` will be replaced with a function call to `state_contract.get_runtime_gitignore_entries()`. This ensures the ignore list is always consistent with the contract. The function returns path patterns for all project-root surfaces where `authority == LOCAL_RUNTIME` or `git_class == IGNORED`.

### D4: Migration strategy

A new migration `m_2_0_9_state_gitignore.py` calls `GitignoreManager.ensure_entries()` with the runtime gitignore entries from the contract. This is idempotent — entries already present are skipped. The migration version matches the next spec-kitty version.

### D5: Constitution surface classification

Constitution surfaces are classified in the contract with their actual current Git policy (`INSIDE_REPO_NOT_IGNORED` for `answers.yaml`, `references.yaml`, `library/**`; `IGNORED` for `governance.yaml`, `directives.yaml`, `metadata.yaml`, `context-state.json`). The notes field records "Git boundary decision deferred to constitution cleanup sprint". No `.gitignore` changes for these surfaces.

### D6: Test strategy — both integration and unit

- **Unit test**: `test_state_contract.py` — validates contract completeness (all audit surfaces present), enum consistency, `to_dict()` serialization, helper function correctness
- **Integration test (A)**: `test_gitignore_contract.py` — validates that every `LOCAL_RUNTIME` project surface has a matching entry in the actual repo `.gitignore`
- **Integration test (B)**: `test_gitignore_contract.py` — validates that `GitignoreManager.RUNTIME_PROTECTED_ENTRIES` (now derived) matches the contract
- **Unit test**: `test_state_doctor.py` — validates doctor output for various filesystem states (surfaces present/absent, ignored/not-ignored)
- **Migration test**: `test_state_gitignore_migration.py` — validates idempotent application on fresh and pre-existing gitignore

## Module Interfaces

### `state_contract.py` — Public API

```python
# Enums
class StateRoot(str, Enum):
    PROJECT = "project"           # .kittify/
    FEATURE = "feature"           # kitty-specs/<feature>/
    GLOBAL_RUNTIME = "global_runtime"  # ~/.kittify/
    GLOBAL_SYNC = "global_sync"   # ~/.spec-kitty/
    GIT_INTERNAL = "git_internal" # .git/spec-kitty/

class AuthorityClass(str, Enum):
    AUTHORITATIVE = "authoritative"
    DERIVED = "derived"
    COMPATIBILITY = "compatibility"
    LOCAL_RUNTIME = "local_runtime"
    SECRET = "secret"
    GIT_INTERNAL = "git_internal"
    DEPRECATED = "deprecated"

class GitClass(str, Enum):
    TRACKED = "tracked"
    IGNORED = "ignored"
    INSIDE_REPO_NOT_IGNORED = "inside_repo_not_ignored"
    GIT_INTERNAL = "git_internal"
    OUTSIDE_REPO = "outside_repo"

class StateFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    JSONL = "jsonl"
    SQLITE = "sqlite"
    MARKDOWN = "markdown"
    TEXT = "text"
    LOCKFILE = "lockfile"
    DIRECTORY = "directory"
    SYMLINK = "symlink"

# Frozen dataclass
@dataclass(frozen=True)
class StateSurface:
    name: str
    path_pattern: str
    root: StateRoot
    format: StateFormat
    authority: AuthorityClass
    git_class: GitClass
    owner_module: str
    creation_trigger: str
    deprecated: bool = False
    notes: str = ""
    def to_dict(self) -> dict: ...

# Registry
STATE_SURFACES: tuple[StateSurface, ...] = (...)

# Helpers
def get_surfaces_by_root(root: StateRoot) -> list[StateSurface]: ...
def get_surfaces_by_git_class(git_class: GitClass) -> list[StateSurface]: ...
def get_surfaces_by_authority(authority: AuthorityClass) -> list[StateSurface]: ...
def get_runtime_gitignore_entries() -> list[str]: ...
```

### `state/doctor.py` — Public API

```python
@dataclass
class StateRootInfo:
    name: str            # "project", "global_runtime", "global_sync"
    label: str           # Human-readable label
    resolved_path: Path  # Actual filesystem path
    exists: bool         # Whether the directory exists on disk

@dataclass
class SurfaceCheckResult:
    surface: StateSurface
    present: bool           # Exists on disk
    gitignore_covered: bool # Matched by .gitignore (for repo-local surfaces)
    warning: str | None     # Non-None if unsafe (runtime + not ignored + present)

@dataclass
class StateRootsReport:
    roots: list[StateRootInfo]
    surfaces: list[SurfaceCheckResult]
    warnings: list[str]

    @property
    def healthy(self) -> bool: ...

    def to_dict(self) -> dict: ...

def check_state_roots(repo_root: Path) -> StateRootsReport: ...
```

### `cli/commands/doctor.py` — CLI Surface

```python
app = typer.Typer(name="doctor", help="Project health diagnostics")

@app.command(name="state-roots")
def state_roots(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show state roots, surface classification, and safety warnings."""
```

## Gitignore Entries Added By This Sprint

These entries will be added to `.gitignore` via migration and enforced by `GitignoreManager`:

```gitignore
# Runtime state (machine-local, never commit)
.kittify/runtime/
.kittify/merge-state.json
.kittify/events/
.kittify/dossiers/
```

Existing entries that are already covered (no change needed):
- `.kittify/.dashboard` — already ignored
- `.kittify/workspaces/` — already ignored
- `.kittify/missions/` — already ignored
- `.kittify/constitution/context-state.json` — already ignored
- `.kittify/constitution/directives.yaml` — already ignored
- `.kittify/constitution/governance.yaml` — already ignored
- `.kittify/constitution/metadata.yaml` — already ignored

Constitution surfaces explicitly NOT changed:
- `.kittify/constitution/interview/answers.yaml` — classified, decision deferred
- `.kittify/constitution/references.yaml` — classified, decision deferred
- `.kittify/constitution/library/**` — classified, decision deferred

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration adds gitignore entries that a user has intentionally tracked | Low | Low | Migration uses `ensure_entries()` which is additive-only; existing tracked files remain tracked until user explicitly removes them |
| Contract becomes stale as new state surfaces are added | Medium | Medium | Test asserts contract completeness against known audit inventory; future features should update contract |
| Top-level `spec-kitty doctor` conflicts with existing command names | Low | High | Verified: no existing `doctor` command at top level. `agent status doctor` remains unchanged |

## Complexity Tracking

No constitution violations to justify.
