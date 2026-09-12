# Phase 1 Data Model — Mission Completion Terminal State

No new persisted store; this mission adds fields/derivations over the existing append-only
status event log. No schema migration (NFR-002).

## Entities

### 1. Cancellation Provenance (on the `canceled` status event)
- **Home**: an event in `status.events.jsonl` with `to_lane == "canceled"`.
- **Fields used/added**:
  - `reason: str | None` — existing; the human note.
  - `reason_source: "operator" | "synthetic" | None` — **new first-class field on `StatusEvent`**
    (`status/models.py`, round-tripped in `to_dict`/`from_dict`), set at the emit site
    (`tasks_move_task.py`). `operator` iff the reason came from a non-empty `--note`. `None` for
    non-cancel events (backward-compatible default). Not `policy_metadata`; not a reduce-time template
    match.
  - `actor`, `at`, `force` — existing; carried into reporting.
- **Invariant**: a cancellation is *accept-eligible* iff `reason_source == "operator"` (a
  non-empty operator note). The CLI's auto-synthesized `"Force move to canceled"` /
  `"move-task: …"` default is `synthetic` and never accept-eligible.
- **Legacy rule**: for events predating `reason_source`, a `reason` that does not match the
  known synthetic templates is treated as `operator` (NFR-002).

### 2. Reduced snapshot — cancellation slot
- **Home**: per-WP dict from `reduce()` (`status/reducer.py:166-177`).
- **Field added**: `cancellation_reason: str | None` (+ its `reason_source`), projected only
  when `lane == "canceled"`. All other lanes unchanged (NFR-002).
- **Invariant**: the projection is derived purely from the event log (C-002); the reducer
  stays deterministic and its golden tests are updated in lockstep.

### 3. Acceptable-Ending Decision (predicate)
- **Home**: `is_acceptable_ending(lane, *, has_provenance) -> bool` in `status_lanes.py`.
- **Truth table**:

  | lane | has_provenance | acceptable ending |
  |------|----------------|-------------------|
  | `approved` | — | ✅ |
  | `done` | — | ✅ |
  | `canceled` | true | ✅ |
  | `canceled` | false | ❌ (structured blocker) |
  | any other | — | ❌ |

- **Consumers**: accept (`acceptance/__init__.py`, replacing `_ACCEPTED_READY_LANES`),
  merge (`executor.py` + `policy/merge_gates.py`), dependency gate (`dependency_graph.py`).
  Single source of truth.
- **Companion accessor**: `has_operator_provenance(wp_snapshot) -> bool` (co-located in
  `status_lanes.py`) — the one reader consumers call so `reason_source == "operator"` is never
  inlined at 3 sites (avoids a whack-a-field regression).

### 4. `canceled_wps` report entry (accept `--json`)
- **Shape** (pinned, NFR-003): `{ "wp_id": str, "reason": str, "actor": str, "at": str (ISO-8601) }`.
- **Rule**: appears only for accept-eligible cancellations; a non-provenance cancellation
  appears in `blockers`, not here.

### 5. Post-Integration Trigger (FR-007 detector)
- **Home**: authoring-time check over a work package's acceptance-criteria / subtask text.
- **Fields**: `wp_id`, `matched_phrase`, `criterion_excerpt`.
- **Signal**: membership in an enumerable trigger-phrase set (e.g. "after merge", "on a
  branch the forge will run", "consecutive runs", "merge-blocked-when-absent"), validated
  against a fixed labeled corpus. Advisory only — produces a warning record, never a block.

## State transition (unchanged matrix, C-001)

The nine-lane matrix is untouched. This mission changes only *how downstream consumers
interpret* the existing terminal `canceled` lane:

```
canceled (terminal)  ──has operator provenance──▶  acceptable ending (accept ✅, merge skips WP, dep resolved)
canceled (terminal)  ──synthetic reason only──▶    structured blocker (accept ❌)
```
