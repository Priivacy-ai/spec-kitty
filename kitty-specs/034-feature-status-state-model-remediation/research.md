# Research: Feature Status State Model Remediation

**Feature**: 034-feature-status-state-model-remediation
**Date**: 2026-02-08

## R-1: ULID Availability

**Decision**: Use existing `ulid` package already in the project dependency tree.

**Rationale**: The `sync/emitter.py` module already imports `ulid` and uses `_generate_ulid()` with the pattern:

```python
if hasattr(ulid, "new"):
    return ulid.new().str
return str(ulid.ULID())
```

The `status/models.py` module can reuse this same generation pattern. No new dependency needed.

**Alternatives considered**:

- `uuid4` — not lexicographically sortable, loses time-ordering property
- Custom timestamp-based IDs — reinventing ULID poorly

## R-2: Existing Lane Values in Codebase

**Decision**: Current codebase uses exactly 4 lanes: `planned`, `doing`, `for_review`, `done`.

**Evidence**:

- `tasks_support.py:28`: `LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")`
- `frontmatter.py:288`: `valid_lanes = ["planned", "doing", "for_review", "done"]`
- `merge/status_resolver.py:123-135`: `LANE_PRIORITY = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}`

All three locations must be updated to the 7-lane canonical set. The `doing` → `in_progress` rename requires alias support at input boundaries.

**Risk**: Existing WP files in kitty-specs/ have `lane: doing` in frontmatter. The migration command must handle this, and the frontmatter validator must accept `doing` as an alias during the transition period.

## R-3: Current move_task Flow

**Decision**: The existing `move_task()` in `cli/commands/agent/tasks.py` has a well-defined flow that can be cleanly refactored to delegate to `status.emit`.

**Current flow** (lines 592-898):

1. `ensure_lane(to)` — validates target lane
2. Feature detection and branch checkout
3. Locate WP file
4. Validation: agent ownership, review feedback, unchecked subtasks, uncommitted changes
5. `set_scalar(frontmatter, "lane", target)` — update frontmatter
6. Update assignee, agent, shell_pid, review_status, reviewed_by
7. Append activity log history entry
8. Write file to disk
9. Auto-commit (if enabled)
10. `emit_wp_status_changed()` — SaaS telemetry

**Delegation strategy**: Steps 1-4 stay in `move_task()` (pre-validation). Steps 5-10 are replaced by a call to `status.emit()` which handles: transition validation → event append → materialize → update views → SaaS emit. The `move_task` function passes through additional fields (assignee, review_status, etc.) as event metadata.

## R-4: Merge Conflict Resolution Pattern

**Decision**: Replace monotonic "most done wins" with rollback-aware resolution.

**Current bug** (identified in PRD):

```python
# status_resolver.py — resolve_lane_conflict()
LANE_PRIORITY = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
# Always picks the "more done" lane — ignores reviewer rollback
```

**Problem scenario**: Branch A merges `for_review → done`. Branch B has `for_review → in_progress` (reviewer requested changes with `review_ref`). Current resolver picks `done` because it has higher priority. This silently overrides a legitimate review rejection.

**Solution**: In the event log model, rollback detection is natural:

1. Events with `review_ref` are marked as reviewer rollbacks
2. During merge (concatenate + deduplicate + sort), rollback events override concurrent forward events for the same WP
3. The reducer applies this precedence during state computation

**For Phase 0** (before event log exists): Update `resolve_lane_conflict()` to detect rollback signals in frontmatter history entries. If the "theirs" side has a review rollback entry newer than the "ours" forward transition, prefer "theirs".

## R-5: SaaS Fan-Out on 0.1x

**Decision**: SaaS emission is a no-op on 0.1x. The canonical local model operates independently.

**Evidence**: The `sync/` module with WebSocket client, auth, and event emission only exists on `2.x`. The `0.1x` line (main branch) does not have this infrastructure.

**Implementation**: The `status.emit` orchestration function checks if `sync.events` is importable. On 0.1x, the import will fail gracefully and SaaS emission is skipped. The canonical event log, reducer, and materialization all operate without any SaaS dependency.

**Alternative considered**: Adding a stub `sync/events.py` to 0.1x — rejected because it adds unnecessary code to a stabilizing branch.

## R-6: Atomic Write Concerns

**Decision**: Use write-then-rename pattern for `status.json`. Append-only for `status.events.jsonl`.

**JSONL append**: Python's `open(path, "a")` is safe for single-writer scenarios. Multi-agent concurrent writes are resolved at git merge time (line concatenation + deduplication). Each agent generates unique ULIDs, so deduplication handles overlapping appends.

**JSON snapshot**: Write to a temporary file, then `os.replace()` to the target path. This ensures `status.json` is never partially written (atomic on POSIX; near-atomic on Windows via rename).

**Failure mode**: If the process crashes between JSONL append and JSON materialization, `status.json` will be stale. Running `status materialize` recovers the correct state from the canonical log. This is safe because the log is the authority, not the snapshot.

## R-7: Phase Configuration Precedence

**Decision**: Three-tier precedence with explicit source tracking.

**Resolution**:

1. `meta.json.status_phase` (per-feature override) — highest
2. `config.yaml.status.phase` (global default) — middle
3. Built-in default: `1` (dual-write) — lowest

**`status validate` output**:

```
Phase: 2 (source: meta.json override for 034-feature-status-state-model-remediation)
```

or

```
Phase: 1 (source: global default from .kittify/config.yaml)
```

**CI guardrail**: `status validate` checks that the effective phase is not greater than the maximum allowed for the branch. On 0.1x, max phase is 2. Phase 3 features (reconcile --apply) are gated behind a branch-aware check.

## R-8: spec-kitty-events Library Integration

**Decision**: The vendored `spec_kitty_events/` library provides Lamport clocks and event models that complement (but do not replace) the new `status/` package.

**Relationship**:

- `spec_kitty_events/models.py` defines `Event` for SaaS sync events (ULID, Lamport clock, node_id)
- `status/models.py` defines `StatusEvent` for canonical local events (ULID, feature_slug, wp_id, lanes)
- These are different concerns: SaaS events are telemetry, canonical events are state authority
- The `status.emit` path creates a `StatusEvent`, appends it to JSONL, then *optionally* creates a SaaS `Event` via `sync/events.py`

**No direct dependency**: `status/` does not import from `spec_kitty_events/`. They are separate packages with different lifecycles. The fan-out from canonical to SaaS happens at the orchestration layer, not the model layer.
