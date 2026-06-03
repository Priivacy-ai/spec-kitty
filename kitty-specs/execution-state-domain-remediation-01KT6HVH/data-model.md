# Data Model: Execution-State Domain Remediation — #1619 Strangler Fig

**Phase 1 output for**: [plan.md](plan.md)  
**Date**: 2026-06-03

---

## New Types (WP04)

### `ActiveWPStatus`

Frozen dataclass in `src/specify_cli/status/aggregate.py`. Read projection returned by `MissionStatus.claim()`.

```python
@dataclass(frozen=True)
class ActiveWPStatus:
    wp_id: str                        # e.g. "WP01"
    current_lane: Lane                # from status/models.py
    last_event: StatusEvent | None    # most recent event from the log
```

**Invariants:**
- `current_lane` is always authoritative from the coord-aware read path (never stale primary)
- `last_event` may be `None` if no events exist yet (newly bootstrapped WP)

---

### `MissionStatus`

Frozen dataclass in `src/specify_cli/status/aggregate.py`. Aggregate root for mission status reads and writes.

```python
@dataclass(frozen=True)
class MissionStatus:
    mission_slug: str
    mission_id: str | None
    mid8: str                          # first 8 chars of mission_id, or "" if None
    topology: Literal["legacy", "coordination"]
    read_dir: Path                     # the authoritative status directory

    @classmethod
    def load(cls, repo_root: Path, mission_slug: str) -> "MissionStatus":
        """Resolve topology once; return authoritative aggregate. Fail-closed for coord-topology."""
        ...

    def claim(self, wp_id: str) -> ActiveWPStatus:
        """Return current lane state for a WP from the coord-aware read path."""
        ...

    def transition(self, request: TransitionRequest) -> StatusEvent:
        """Validate and apply a lane transition via BookkeepingTransaction internally."""
        ...

    def save(self, *, operation: str) -> CommitReceipt:
        """Persist staged transitions via BookkeepingTransaction."""
        ...
```

**Topology resolution** (inside `load()`):
- Calls `workspace/root_resolver.py` and `missions/_resolve_planning_branch.py` to determine if the mission uses coord-topology (has a coordination branch) or legacy.
- `read_dir` for legacy: `repo_root / "kitty-specs" / mission_slug`
- `read_dir` for coord-topology: the coordination branch checkout path

**Fail-closed contract**: If topology is `"coordination"` and the coord authority path is unavailable, `load()` raises `CoordAuthorityUnavailable` — no silent fallback to `legacy` path.

**Placement in `status/__init__.py`**: Both `MissionStatus` and `ActiveWPStatus` added to `__all__` after creation.

---

## Extended Types (WP05)

### `MissionRunSnapshot` (extended)

Pydantic `BaseModel` in `src/runtime/next/_internal_runtime/schema.py`. Fields added as optional with `None` defaults to preserve backward-compatibility with existing on-disk `state.json` files.

```python
class MissionRunSnapshot(BaseModel):
    # Existing fields (unchanged):
    run_id: str
    mission_key: str
    # ... other existing fields ...

    # New fields (WP05):
    mission_id: str | None = None     # canonical ULID from meta.json
    mission_slug: str | None = None   # human-readable slug
```

**Backward-compatibility**: Pydantic silently defaults missing fields to `None` when deserializing existing `state.json` files. No migration needed.

**Write behavior**: New runs created after WP05 lands will have `mission_id` and `mission_slug` populated by `start_mission_run`. Existing runs keep `None` unless explicitly backfilled.

---

### `MissionRunRef` (extended)

Pydantic `BaseModel` in `src/runtime/next/_internal_runtime/engine.py`. Same optional-with-default pattern.

```python
class MissionRunRef(BaseModel):
    # Existing fields (unchanged):
    run_id: str
    run_dir: str
    mission_key: str

    # New fields (WP05):
    mission_id: str | None = None
    mission_slug: str | None = None
```

**Plumbing**: `start_mission_run` calls `_resolve_mission_ulid(mission_slug, repo_root)` to get the ULID, then passes both to the `MissionRunSnapshot` and `MissionRunRef` constructors.

---

## State Transitions (relevant to WP04)

`MissionStatus.transition()` delegates to the existing FSM in `status/transitions.py`. No new transitions are introduced. The nine-lane state machine (planned → claimed → in_progress → for_review → in_review → approved → done, plus blocked and canceled) is unchanged.

**Domain invariant enforcement**: `status/transitions.validate_transition()` is called inside `MissionStatus.transition()` before `BookkeepingTransaction.acquire()`. Callers never bypass validation by calling `BookkeepingTransaction` directly.

---

## Boundary Rules (relevant to WP03)

**Allowed** (internal domain plumbing):
- `coordination/status_transition.py` → imports `status/emit`, `status/reducer`, etc. (exempt)
- `status/aggregate.py` → imports `status/models`, `status/transitions`, `status/store`, `status/reducer` (internal, allowed)

**Prohibited** (must be fixed by WP03):
- Any file under `src/specify_cli/` outside `status/` → direct import of `status.<submodule>`
- Any file under `src/runtime/` → direct import of `status.<submodule>`
- Any file under `tests/` (except via `from specify_cli.status import ...`)

---

## Feature-Runs Index (relevant to WP05)

`.kittify/runtime/feature-runs.json` write site in `runtime_bridge.py` (~line 2052–2057) is updated to include `mission_id` and `mission_slug` alongside the existing slug→run mapping. This enables forward lookup (slug→run) to also carry the canonical ULID for reverse resolution.

---

## Files Changed by WP

| WP | File | Change type |
|----|------|------------|
| WP01 | `architecture/3.x/adr/2026-06-03-1-*.md` | New |
| WP01 | `architecture/3.x/adr/2026-06-03-2-*.md` | New |
| WP01 | `architecture/3.x/adr/2026-06-03-3-*.md` | New |
| WP01 | `src/specify_cli/glossary/` (glossary YAML/MD) | Extend |
| WP02 | `tests/architectural/test_execution_context_parity.py` | New |
| WP02 | `.github/workflows/ci.yml` (path filter) | Extend |
| WP03 | `tests/architectural/test_status_module_boundary.py` | New |
| WP03 | `src/specify_cli/status/__init__.py` | Promote symbols |
| WP03 | Various files under `src/` | Fix ~245 bypass imports |
| WP04 | `src/specify_cli/status/aggregate.py` | New |
| WP04 | `src/specify_cli/status/__init__.py` | Export MissionStatus, ActiveWPStatus |
| WP04 | `src/specify_cli/cli/commands/agent/status.py` | Migrate to MissionStatus |
| WP05 | `src/runtime/next/_internal_runtime/schema.py` | Extend MissionRunSnapshot |
| WP05 | `src/runtime/next/_internal_runtime/engine.py` | Extend MissionRunRef, plumb 6 sites |
| WP05 | `src/runtime/next/runtime_bridge.py` | Update feature-runs.json write |
| WP06 | `src/runtime/next/runtime_bridge.py` | Route query-mode through resolve_action_context |
| WP06 | `src/specify_cli/cli/commands/agent/workflow.py` | Route fix-mode through resolve_action_context |
| WP06 | Various deleted helpers | Delete unreachable path-builders |
