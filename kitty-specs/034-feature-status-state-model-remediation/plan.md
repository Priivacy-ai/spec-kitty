# Implementation Plan: Feature Status State Model Remediation

**Branch**: `034-feature-status-state-model-remediation` | **Date**: 2026-02-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/034-feature-status-state-model-remediation/spec.md`

## Summary

Replace spec-kitty's scattered status authority (frontmatter lanes, meta.json, tasks.md checkboxes) with a canonical append-only event log (`status.events.jsonl`) per feature plus a deterministic reducer producing `status.json` snapshots and generated compatibility views. Implement a strict 7-lane state machine with guard conditions, force-audit requirements, rollback-aware conflict resolution, and done-evidence enforcement. Deliver on both `2.x` and `0.1x` branch lines with maximum parity.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (frontmatter), ulid (event IDs, already in project)
**Storage**: Filesystem — append-only JSONL (`status.events.jsonl`), JSON snapshot (`status.json`), YAML frontmatter (compatibility)
**Testing**: pytest with 90%+ coverage, mypy --strict
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI)
**Project Type**: Single Python package (existing `src/specify_cli/`)
**Performance Goals**: CLI operations < 2 seconds; reducer handles 100+ WPs without lag
**Constraints**: No new external dependencies beyond what's already in project; offline-capable (no network required for canonical model)
**Scale/Scope**: Typical features have 5-15 WPs; event logs will be 10s-100s of events per feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ | PASS | All new code targets 3.11+ |
| typer CLI framework | PASS | New `agent status` command group uses typer |
| rich console output | PASS | Status commands use Rich for formatted output |
| pytest 90%+ coverage | PASS | Full test suite for transitions, reducer, validation |
| mypy --strict | PASS | All new modules will have type annotations |
| Cross-platform | PASS | JSONL/JSON files, pathlib, no OS-specific calls |
| Git required | PASS | Event log is git-tracked; merge semantics depend on git |
| Two-branch strategy | NOTED | Constitution says "no progressive migration 1.x→2.x" and deferred migration. This feature explicitly requires Phases 0-2 on 0.1x per user direction. The dual-write approach avoids "dual state complexity" the constitution warns against — the canonical model replaces (not coexists with) the old model after cutover. User direction overrides constitution default here. |
| spec-kitty-events library | PASS | `ulid` already available through vendored `spec_kitty_events/`; Lamport clocks available for event ordering |
| No fallback mechanisms | PASS | Fail-fast on invalid transitions, corrupted logs, missing evidence |

**Constitution Conflict Resolution**: The constitution's "deferred migration" principle refers to deferring user-facing YAML→events migration tooling until 2.x is stable. This feature introduces the canonical event model on *both* branches, which is the prerequisite for that future migration — not a violation of the principle. The user has explicitly directed Phases 0-2 on 0.1x.

## Project Structure

### Documentation (this feature)

```
kitty-specs/034-feature-status-state-model-remediation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── spec.md              # Feature specification
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── status/                          # NEW: Canonical status engine
│   ├── __init__.py                  # Public API exports
│   ├── models.py                    # StatusEvent, StatusSnapshot, DoneEvidence, Lane enum
│   ├── transitions.py               # TransitionMatrix, guard conditions, alias resolution
│   ├── reducer.py                   # Deterministic reducer: events → snapshot
│   ├── store.py                     # JSONL append/read, atomic operations
│   ├── reconcile.py                 # Cross-repo drift detection and reconciliation
│   ├── doctor.py                    # Stale claims, orphan detection, health checks
│   ├── phase.py                     # Phase resolution (config.yaml → meta.json → default)
│   └── legacy_bridge.py             # Frontmatter/tasks.md compatibility view generation
│
├── cli/commands/agent/
│   ├── status.py                    # NEW: agent status {emit,materialize,validate,reconcile,doctor}
│   └── tasks.py                     # MODIFIED: move-task delegates to status.emit internally
│
├── frontmatter.py                   # MODIFIED: Expand valid_lanes to 7-lane set + alias
├── tasks_support.py                 # MODIFIED: Expand LANES tuple to 7 canonical lanes
│
├── merge/
│   └── status_resolver.py           # MODIFIED: Rollback-aware conflict resolution
│
├── sync/
│   └── events.py                    # MODIFIED: Add SaaS fan-out hook from status.emit path
│
└── agent_utils/
    └── status.py                    # MODIFIED: Read from status.json when Phase 2 active

tests/
├── specify_cli/
│   └── status/                      # NEW: Unit tests for status engine
│       ├── test_models.py           # Event schema validation
│       ├── test_transitions.py      # Transition legality, guards, force behavior
│       ├── test_reducer.py          # Determinism, idempotency, merge ordering
│       ├── test_store.py            # JSONL I/O, atomic operations
│       ├── test_reconcile.py        # Drift detection, reconciliation events
│       ├── test_doctor.py           # Stale claims, orphan detection
│       ├── test_phase.py            # Phase resolution precedence
│       ├── test_legacy_bridge.py    # Compatibility view generation
│       └── test_conflict_resolution.py  # Rollback-aware merge semantics
│
├── integration/
│   ├── test_status_emit_flow.py     # End-to-end: emit → append → materialize → fan-out
│   ├── test_dual_write.py           # Phase 1 dual-write behavior
│   ├── test_read_cutover.py         # Phase 2 canonical-only reads
│   └── test_migration.py            # Legacy frontmatter → event log bootstrap
│
└── cross_branch/
    └── test_parity.py               # Shared fixtures verifying 2.x/0.1x produce identical output
```

**Structure Decision**: New `src/specify_cli/status/` package parallels existing `sync/` and `merge/` packages. CLI entrypoint at `cli/commands/agent/status.py`. Existing modules receive targeted modifications (lane expansion, delegation, rollback awareness).

## Architectural Decisions

### AD-1: Event Schema

Each event in `status.events.jsonl` is a single JSON line:

```json
{
  "event_id": "01HXYZ...",
  "feature_slug": "034-feature-status-state-model-remediation",
  "wp_id": "WP01",
  "from_lane": "planned",
  "to_lane": "claimed",
  "at": "2026-02-08T12:00:00Z",
  "actor": "claude",
  "force": false,
  "reason": null,
  "execution_mode": "worktree",
  "review_ref": null,
  "evidence": null
}
```

**ULID for event_id**: Already available in the project via the `ulid` package used by `sync/emitter.py`. Provides lexicographic sortability and global uniqueness.

**Sorting key**: Primary = `at` (ISO timestamp), secondary = `event_id` (ULID — inherently time-ordered). This gives deterministic total ordering even across distributed writers.

### AD-2: Reducer Algorithm

```
1. Read all events from status.events.jsonl
2. Validate each line is valid JSON (fail-fast on corruption)
3. Deduplicate by event_id (keep first occurrence)
4. Sort by (at, event_id) ascending
5. For each WP, reduce to final state:
   a. Apply rollback-aware precedence (see AD-4)
   b. Track current lane per WP
6. Serialize to status.json with sorted keys (determinism)
```

**Byte-identical output**: Use `json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False)` with a trailing newline. Same input always produces same output.

### AD-3: Transition Matrix

```python
CANONICAL_LANES = ("planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled")

LANE_ALIASES = {"doing": "in_progress"}

ALLOWED_TRANSITIONS = {
    ("planned", "claimed"),
    ("claimed", "in_progress"),
    ("in_progress", "for_review"),
    ("for_review", "done"),
    ("for_review", "in_progress"),
    ("in_progress", "planned"),
    # "any -> blocked" (except done, canceled)
    ("planned", "blocked"),
    ("claimed", "blocked"),
    ("in_progress", "blocked"),
    ("for_review", "blocked"),
    # "blocked -> in_progress"
    ("blocked", "in_progress"),
    # "any (except done) -> canceled"
    ("planned", "canceled"),
    ("claimed", "canceled"),
    ("in_progress", "canceled"),
    ("for_review", "canceled"),
    ("blocked", "canceled"),
}
# done is terminal unless forced
```

**Guard conditions**: Implemented as validator functions per transition. Each returns `(ok: bool, error: str | None)`. The `emit` command calls all applicable guards before appending.

### AD-4: Rollback-Aware Conflict Resolution

Current `merge/status_resolver.py` uses monotonic "most done wins" via `LANE_PRIORITY`. This is the bug the PRD identifies.

**New algorithm for event log merge**:
1. Concatenate event logs from both branches
2. Deduplicate by `event_id`
3. Sort by `(at, event_id)`
4. For each WP, if concurrent events exist (same `from_lane`):
   - If one is a reviewer rollback (`for_review → in_progress` with `review_ref`), it wins
   - Otherwise, use timestamp ordering (later event wins)
5. Validate final state against transition matrix

**Concurrency detection**: Two events are concurrent if they share the same `from_lane` for the same WP and neither is an ancestor of the other (determined by event_id ordering — if neither precedes the other in the sorted log).

### AD-5: Phase Configuration

```yaml
# .kittify/config.yaml (global default)
status:
  phase: 1  # 0=hardening, 1=dual-write, 2=read-cutover

# kitty-specs/<feature>/meta.json (per-feature override)
{
  "status_phase": 2  # Overrides global for this feature
}
```

**Resolution order**: `meta.json.status_phase` > `config.yaml.status.phase` > built-in default (1)

**Phase behaviors**:
- **Phase 0**: Transition matrix enforced, force-audit required. No event log yet. Existing frontmatter is authority.
- **Phase 1**: Dual-write. Every transition appends canonical event AND updates frontmatter. Read from frontmatter (existing behavior). `status validate` warns on drift.
- **Phase 2**: Canonical read. Read from `status.json` only. Frontmatter regenerated as compatibility view. `status validate` fails on drift.

**0.1x cap**: On 0.1x branch, phase defaults to 1 and is capped at 2 (Phase 3 reconcile operates in `--dry-run` only).

### AD-6: Unified Fan-Out

```
CLI command (e.g., move-task, status emit)
    → status.transitions.validate_transition()
    → status.store.append_event()
    → status.reducer.materialize()
    → status.legacy_bridge.update_views()  (Phase 1+2)
    → sync.events.emit_wp_status_changed()  (when SaaS configured)
```

The `status.emit` path is the single orchestration point. `tasks.py:move_task()` delegates to it internally. `sync/events.py` remains the SaaS downstream — it receives the event *after* canonical persistence, not before.

### AD-7: Legacy Bridge

`legacy_bridge.py` handles:
1. **Write**: After materialization, update WP frontmatter `lane` fields and tasks.md status sections from `status.json`
2. **Read (Phase 1 only)**: Existing code reads from frontmatter — no changes needed during Phase 1
3. **Read (Phase 2)**: `agent_utils/status.py` reads from `status.json` instead of frontmatter
4. **Migration**: Bootstrap events from current frontmatter state (one event per WP, `doing` → `in_progress`)

### AD-8: move-task Delegation

```python
# cli/commands/agent/tasks.py — move_task() changes:

# Before (current):
#   1. ensure_lane(to)
#   2. validate prerequisites
#   3. set_scalar(frontmatter, "lane", target)
#   4. write file
#   5. git commit
#   6. emit_wp_status_changed()

# After:
#   1. resolve_lane_alias(to)  # "doing" → "in_progress"
#   2. validate prerequisites (unchanged)
#   3. status.emit(feature_slug, wp_id, to_lane, actor, ...)
#      ↳ validate_transition() → append_event() → materialize() → update_views() → saas_emit()
#   4. git commit (includes both status.events.jsonl and frontmatter changes)
#   5. output result (unchanged)
```

The `move_task` function retains its existing validation logic (subtask checks, review readiness, agent ownership) but delegates the state mutation to `status.emit`.

## Integration Points

### Modified Existing Code

| File | Change | Risk |
|------|--------|------|
| `tasks_support.py` | Expand `LANES` tuple to 7 lanes + add alias map | Low — additive |
| `frontmatter.py` | Expand `valid_lanes` in `validate()` to 7 lanes | Low — additive |
| `cli/commands/agent/tasks.py` | `move_task()` delegates to `status.emit` | Medium — core flow change |
| `merge/status_resolver.py` | Replace `LANE_PRIORITY` monotonic resolver with rollback-aware logic | Medium — changes merge behavior |
| `sync/events.py` | No change — already called downstream | None |
| `agent_utils/status.py` | Read from `status.json` when Phase 2 active | Low — conditional path |

### New Code

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `status/__init__.py` | Public API exports | 30 |
| `status/models.py` | StatusEvent, StatusSnapshot, DoneEvidence, Lane enum | 150 |
| `status/transitions.py` | Matrix, guards, alias resolution, validation | 200 |
| `status/reducer.py` | Deterministic reducer with rollback awareness | 180 |
| `status/store.py` | JSONL append/read, atomic operations | 120 |
| `status/reconcile.py` | Cross-repo drift detection | 200 |
| `status/doctor.py` | Health checks, stale detection | 150 |
| `status/phase.py` | Phase config resolution | 80 |
| `status/legacy_bridge.py` | Compatibility view generation | 150 |
| `cli/commands/agent/status.py` | CLI commands: emit, materialize, validate, reconcile, doctor | 350 |

**Estimated new code**: ~1,600 lines of implementation + ~2,000 lines of tests

## Migration Strategy

### Phase 0: Immediate Hardening

**Scope**: Enforce transition matrix and force-audit in existing `move_task`. No event log yet.

1. Add `status/transitions.py` with the 7-lane matrix
2. Modify `tasks_support.py` and `frontmatter.py` to accept 7 lanes
3. Wire `move_task()` to call `transitions.validate_transition()` before persisting
4. Require `actor` + `reason` for force transitions
5. Update `merge/status_resolver.py` with rollback awareness (even before event log, the resolver should prefer rollback signals)

### Phase 1: Canonical Log Introduction (Dual Write)

**Scope**: Introduce event log, dual-write on every transition.

1. Add `status/models.py`, `status/store.py`, `status/reducer.py`
2. Add `status.emit` orchestration: validate → append → materialize → update views → SaaS
3. Wire `move_task()` to delegate to `status.emit`
4. `status validate` warns on drift (non-blocking)
5. Legacy frontmatter remains authoritative for reads
6. Add migration command for existing features

### Phase 2: Canonical Read Cutover

**Scope**: Read from `status.json`, frontmatter becomes generated view.

1. `agent_utils/status.py` reads from `status.json` when phase=2
2. `status validate` fails on drift (blocking)
3. Frontmatter regenerated after every materialization
4. No manual frontmatter edits respected as authority

### Phase 3: Cross-Repo Reconciliation

**Scope**: Reconcile planning state with implementation reality.

1. Add `status/reconcile.py` — scan target repos for WP-linked commits
2. `status reconcile --dry-run` available on both branches
3. `status reconcile --apply` on 2.x only (0.1x dry-run only)
4. `status doctor` for operational hygiene

## Backport Strategy (2.x → 0.1x)

1. Implement full feature on `2.x` first
2. Create backport branch from `main` (0.1x target)
3. Cherry-pick commits that apply cleanly
4. Adapt SaaS fan-out to no-op on 0.1x (sync/ infrastructure absent)
5. Verify cross-branch parity with shared test fixtures
6. Cap Phase 3 to `--dry-run` only on 0.1x
7. Document parity matrix for any unavoidable deltas

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dual-branch delivery | User explicitly requires Phases 0-2 on 0.1x to prevent long-term divergence | Single-branch (2.x only) would let 0.1x behavior diverge permanently |
| Dual-write phase | PRD mandates non-breaking migration; cannot skip directly to canonical reads | Direct cutover would break all existing automation and slash commands |
| 7-lane state machine (vs current 4) | PRD requires claimed/blocked/canceled for proper lifecycle tracking | 4-lane model cannot express blocking, abandonment, or pre-work claiming |
