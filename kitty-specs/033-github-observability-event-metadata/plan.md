# Implementation Plan: GitHub Observability Event Metadata
*Path: kitty-specs/033-github-observability-event-metadata/plan.md*

**Branch**: `033-github-observability-event-metadata` | **Date**: 2026-02-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/033-github-observability-event-metadata/spec.md`

## Summary

Enrich every CLI-emitted sync event with three new envelope fields — `git_branch`, `head_commit_sha`, and `repo_slug` — so the SaaS can correlate events with GitHub repositories, branches, and commits. Implementation adds a new `git_metadata.py` module for per-event volatile git state resolution (branch/SHA with 2s TTL cache), extends `ProjectIdentity` with a persisted `repo_slug` override, and injects all three fields into `emitter.py::_emit()` alongside existing identity fields.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: subprocess (git CLI), pathlib, dataclasses, typing, time (for TTL)
**Storage**: `.kittify/config.yaml` (repo_slug override persisted alongside existing project identity)
**Testing**: pytest (existing sync test patterns in `tests/sync/`)
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform git CLI)
**Project Type**: Single (CLI tool)
**Performance Goals**: Git metadata resolution < 50ms per event (subprocess overhead); 2s TTL cache amortizes to near-zero for burst emissions
**Constraints**: Non-blocking — git metadata failures must never block event emission. All new fields nullable.
**Scale/Scope**: 8 event types × 3 new fields = 24 field additions (all via single injection point in `_emit()`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | Using existing Python version |
| pytest with 90%+ coverage | PASS | New module gets full unit test coverage |
| mypy --strict | PASS | All new code will have type annotations |
| CLI operations < 2s | PASS | 2s TTL cache ensures no stacking; single git subprocess ~10-30ms |
| Cross-platform | PASS | `subprocess.run(["git", ...])` works on all platforms |
| Git required | PASS | Graceful degradation to null fields when git unavailable |
| No 1.x compatibility | PASS | Feature targets 2.x branch only |
| Additive-only changes | PASS | No existing fields modified; new fields are optional/nullable |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/033-github-observability-event-metadata/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── event-envelope.md  # Updated envelope contract
└── quickstart.md        # Phase 1 output
```

### Source Code (repository root)

```
src/specify_cli/sync/
├── git_metadata.py          # NEW: GitMetadataResolver + repo slug helpers
├── project_identity.py      # MODIFIED: Add repo_slug field to ProjectIdentity
├── emitter.py               # MODIFIED: Inject git metadata fields in _emit()
└── events.py                # UNCHANGED (convenience functions unchanged)

tests/sync/
├── test_git_metadata.py     # NEW: Unit tests for GitMetadataResolver
├── test_events.py           # MODIFIED: Add envelope tests for new fields
├── test_event_emission.py   # MODIFIED: Integration tests for metadata in CLI commands
└── conftest.py              # MODIFIED: Add git_metadata fixtures
```

**Structure Decision**: Follows established `src/specify_cli/sync/` module pattern. New `git_metadata.py` sits alongside `project_identity.py` as a peer module. No new directories needed.

## Design Decisions

### D1: Module Split — `git_metadata.py` vs `project_identity.py`

**Decision**: Create new `git_metadata.py` in `src/specify_cli/sync/`.

**Rationale**: Separation of concerns:
- `project_identity.py` manages **stable, persisted** identity (UUID, slug, node_id, repo_slug override). Resolved once per session.
- `git_metadata.py` manages **volatile, per-event** git state (branch, SHA). Resolved per-event with TTL cache.

**Alternative rejected**: Putting everything in `project_identity.py` — would conflate session-cached and per-event concerns, making the TTL cache logic awkward alongside the existing atomic-write persistence.

### D2: TTL Cache Implementation

**Decision**: Simple time-based cache with 2-second TTL in `GitMetadataResolver`.

**Implementation**: Store `(branch, sha, timestamp)` tuple. On `resolve()`, if `time.monotonic() - cached_time < 2.0`, return cached values. Otherwise, call `git rev-parse`.

**Rationale**: `time.monotonic()` is not affected by system clock changes. 2s TTL balances correctness (events emitted seconds apart reflect real state) vs. performance (burst emissions during finalize-tasks don't spawn dozens of subprocesses).

### D3: Repo Slug Derivation

**Decision**: Extract `owner/repo` from `git remote get-url origin`. Parse both SSH and HTTPS formats. Persist override in `ProjectIdentity.repo_slug`.

**Derivation precedence**:
1. Explicit override in `.kittify/config.yaml` → `project.repo_slug`
2. Auto-derived from `origin` remote URL
3. `None` (no remote, no override)

**Validation**: Override must match `owner/repo` format (exactly one `/`, both segments non-empty). Invalid override → warning + fallback to auto-derived.

### D4: Emitter Integration Point

**Decision**: Single injection point in `emitter.py::_emit()` at line ~467, right after identity resolution.

**Implementation**:
```python
# In _emit(), after identity/team_slug resolution:
git_meta = self._get_git_metadata()

event: dict[str, Any] = {
    # ... existing fields ...
    "project_uuid": ...,
    "project_slug": ...,
    # NEW: git correlation fields
    "git_branch": git_meta.git_branch,
    "head_commit_sha": git_meta.head_commit_sha,
    "repo_slug": git_meta.repo_slug,
}
```

**Rationale**: Centralizes metadata injection — all 8 event types get the fields automatically via the single `_emit()` path. No changes needed to individual `emit_*()` methods.

### D5: EventEmitter Wiring

**Decision**: Lazy-load `GitMetadataResolver` in `EventEmitter` (same pattern as `_get_identity()`).

**Implementation**: Add `_git_resolver: GitMetadataResolver | None` field to `EventEmitter` dataclass. `_get_git_metadata()` method lazily creates it on first call. Resolver is initialized with `repo_root` from `find_repo_root()`.

**Test pattern**: Follows existing `_identity` field pattern — tests can pre-populate `_git_resolver` with a mock or pre-configured instance via the fixture.

### D6: Worktree Awareness

**Decision**: `GitMetadataResolver.resolve()` uses `cwd` parameter (defaults to `Path.cwd()`). When running in a worktree, `Path.cwd()` naturally points to the worktree directory, and `git rev-parse` resolves the worktree's branch/HEAD (not the main repo's).

**Rationale**: No special worktree detection needed. Git's own `rev-parse` is worktree-aware when run from the worktree directory.

### D7: Backward Compatibility

**Decision**: New fields are additive-only. The `_validate_event()` method does NOT check for the new fields (they're envelope metadata, not payload). Batch sync sends them as part of the event dict — the SaaS endpoint accepts unknown fields per JSON tolerance. Offline queue stores the full event dict including new fields.

**No changes to**: `_validate_event()`, `_validate_payload()`, `VALID_EVENT_TYPES`, Event Pydantic model (coordinated separately).
