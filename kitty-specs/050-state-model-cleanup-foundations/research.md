# Research: State Model Cleanup Foundations

## R1: Doctor command placement

**Decision**: New top-level `spec-kitty doctor` command group
**Rationale**: State-roots diagnostics are project-scoped, not feature-scoped. The existing `spec-kitty agent status doctor` is feature-scoped (status events, stale claims, drift). Mixing project-level and feature-level concerns in one command creates confusion. A top-level group provides a natural home for future diagnostics (credential health, queue integrity, etc.).
**Alternatives considered**:
- Subcommand under `spec-kitty agent status doctor --scope state-roots`: Rejected because it overloads a feature-scoped command with project-scoped concerns.
- `spec-kitty ops state-roots`: Rejected because `ops` is for operational actions (e.g., repair), not diagnostics.

## R2: State contract format

**Decision**: Python dataclasses + enums in `state_contract.py`
**Rationale**: All consumers are Python. Enums provide type safety and make drift harder. Frozen dataclasses enforce immutability. The module reads like a typed manifest — data-first, no business logic beyond lookup helpers.
**Alternatives considered**:
- YAML manifest + deserialization: Rejected because it adds a parsing layer, loses type safety, and makes the contract harder to test.
- JSON Schema: Rejected because it would need a separate validation layer and provides less ergonomic Python access.

## R3: GitignoreManager derivation approach

**Decision**: Replace `RUNTIME_PROTECTED_ENTRIES` constant with a call to `state_contract.get_runtime_gitignore_entries()`
**Rationale**: Single source of truth. The contract defines what is runtime state; the manager enforces it. No separate list to keep in sync.
**Implementation detail**: `get_runtime_gitignore_entries()` returns path patterns for project-root surfaces where `authority == LOCAL_RUNTIME` or where `git_class == IGNORED` and `root == PROJECT`. This includes the existing `.dashboard` and `__pycache__` entries plus the new runtime entries.

## R4: Migration versioning

**Decision**: Migration named `m_2_0_9_state_gitignore.py` (next version after current 2.0.8/2.0.9)
**Rationale**: Follows existing convention of version-aligned migration names. The migration is idempotent (uses `ensure_entries()`).
**Note**: If a different version number is needed at release time, the migration can be renamed. The migration registry uses the module itself, not the filename version.

## R5: Test strategy

**Decision**: Both integration and unit tests (option C from planning)
**Rationale**: They catch different failure modes:
- Unit tests validate contract completeness and internal consistency
- Integration test A validates the real `.gitignore` against the contract (catches repo-level drift)
- Integration test B validates that `GitignoreManager` entries match the contract (catches code-level drift)
- Doctor tests validate output for various filesystem states
- Migration tests validate idempotent application

## R6: Gitignore check approach for doctor

**Decision**: Use `git check-ignore` subprocess to test whether a path is covered by gitignore rules
**Rationale**: Parsing `.gitignore` manually is brittle (negation rules, nested gitignore files, global gitconfig excludes). `git check-ignore -q <path>` uses Git's own rule engine and handles all edge cases. Return code 0 = ignored, 1 = not ignored.
**Fallback**: If not in a Git repo, skip the gitignore check and warn that coverage cannot be verified.

## R7: Existing `~/.spec-kitty/` path resolution

**Decision**: Reuse `Path.home() / '.spec-kitty'` inline (matching `sync/config.py` pattern)
**Rationale**: There is no centralized `get_sync_home()` function in the codebase today. The sync module hardcodes `Path.home() / '.spec-kitty'`. Creating a centralized helper would be useful but is beyond this sprint's scope. The state contract records the path pattern; the doctor command resolves it the same way.
**Deferred**: A `get_sync_home()` helper could be added in a later sprint to parallel `get_kittify_home()`.
