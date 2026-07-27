# Phase 0 Research: WP runtime-state eviction

All open design questions were resolved *before* planning — through the seven HiC decisions
(brief §0), the ADR of record, and a four-lens post-spec adversarial squad (2026-07-19). This file
records the decisions in Decision / Rationale / Alternatives form; there are **no** outstanding
`[NEEDS CLARIFICATION]` markers.

## D1 — Off-axis mutation mechanism

- **Decision**: One generic `InnerStateChanged` event carrying a typed `WPInnerStateDelta`, bypassing
  `validate_transition`, folded by the reducer (Option A, realised as a single event).
- **Rationale**: Only option that makes the log a true SSOT for all three off-axis mutations (resume
  PID, subtask marks, notes); reusable; typed delta avoids a new split-brain.
- **Alternatives**: (B) fold onto transitions + `policy_metadata` — complete only for `shell_pid`,
  resume false-stale window; (C) FSM self-edges — redefines the "transition changes lane" invariant.
  Both rejected (ADR §7).

## D2 — Reducer fold semantics

- **Decision**: The reducer **branches on event kind**; lane transitions **preserve** untouched runtime
  slots (per-field independence); annotations skip the lane assignment and apply the typed delta;
  ordering is an **event-kind partition** (annotations in a post-transition pass), not an `at`-interleave.
- **Rationale**: Squad-CRITICAL — `reducer.py::_wp_state_from_event` today rebuilds the per-WP dict
  carrying forward only `force_count`, so a later transition would erase the runtime slots; and at an
  equal `at` a deterministic seed ULID vs a time ULID would order arbitrarily.
- **Alternatives**: naive "fold after by timestamp" (rejected — clobbers slots non-deterministically).

## D3 — Annotation visibility on the read path

- **Decision**: Define a wire/envelope discriminator + a distinct read path so `store.read_events` /
  `is_non_lane_event` surface annotations to `reduce()`; assert (architectural test) an annotation is
  never reduced as a lane transition.
- **Rationale**: Squad-HIGH — today `is_non_lane_event` skips any `event_type`-bearing event and
  `StatusEvent.from_dict` hard-requires `from_lane`/`to_lane`; without reconciliation the annotation is
  structurally invisible or fails the whole event read.

## D4 — Migration ordering & integrity

- **Decision**: `backfill → verify(fail-closed) → reader cutover → writer cutover → delete fallbacks`;
  deterministic namespaced ULIDs ordering after the annotated transition at equal `at`; symmetric-window
  closure (atomic reader/writer switch or dual-write per field).
- **Rationale**: Closes both the B3 clobber window and the squad-HIGH second-polarity window (snapshot-
  first reader ignoring a fresh frontmatter write). Verify must abort before cutover on parity mismatch.
- **Alternatives**: writer-first (rejected — B3 clobber); single-polarity ordering (rejected — leaves the
  reader-before-writer window open).

## D5 — `tracker_refs` classification

- **Decision**: Evict (runtime, event-sourced union delta) AND strike from the static schema /
  `WP_FIELD_ORDER` so it is not dual-homed.
- **Rationale**: It is runtime-written (FR-011/map-requirements); dual-homing would be the exact #2093
  violation. HiC Decision 5.
- **Alternatives**: author-immutable (rejected — removes FR-011 runtime append, guts map-requirements).

## D6 — `review_artifact_override_*` scope

- **Decision**: Evict as a **matched pair** — write (`tasks_materialization.py`) AND read
  (`review/artifacts.py`) + merge-gate recognition — collapsing the coord-mirror duplication.
- **Rationale**: Squad blocker — write-only eviction silently breaks override recognition → false merge
  blocks. HiC Decision 5 keeps it in-scope; the fix is both-halves, not defer.

## D7 — Force-provenance (FR-015)

- **Decision**: Suppress `emit_force` by asking the FSM (`validate_transition` legal force-free with
  edge-specific evidence), not a hard-coded edge list; assert the **persisted** `StatusEvent.force`.
- **Rationale**: Squad empirically proved the five edges ARE exactly the force-free-legal backward set;
  but a hard-coded list rots if the matrix changes, and evidence is edge-specific (`reason` vs
  `review_ref` vs structured `review_result`).
- **Alternatives**: frozen five-edge list (accepted-but-fragile — use FSM instead).

## D8 — Reducer performance gate

- **Decision**: Assert the fold is O(events) with no extra re-reduction pass (structural), not a
  wall-clock threshold.
- **Rationale**: A `<5%` wall-time delta on ~500 events is inside measurement noise; a complexity
  assertion is deterministic and non-flaky.

## Squad empirical findings carried into design (2026-07-19)

- **All ~18 code anchors CONFIRMED, zero drift** (debugger lens) — the spec's file:line map is current.
- **FR-015's five edges are the provably exact force-free-legal backward set** — the `for_review→*`
  dormant-mask hypothesis was falsified; no over-reach, no missed edge.
- **SC-003 red test is red-by-execution**; **SC-007 is double-pinned** by the existing plan-level force
  tests it must re-point.
- **Reducer carries no subtask state today** — FR-002/FR-003 are genuinely net-new.
- **Subtask-parser consolidation is already complete** (no residual duplicate parser to campsite).

## Brownfield discipline (standing procedures applied)

- Characterisation before change: the merged red test + the existing force tests are the behavioural
  anchors; add proof-of-drive lifecycle characterisation before the writer cutover.
- Never break legacy on-disk WPs: the fallback deletes (`workflow_cores`/`done_bookkeeping`) are gated
  strictly behind the FR-011 backfill; do not reorder.
- Reader-before-writer with a verified backfill; fail-closed verify.
