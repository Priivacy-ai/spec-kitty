# Phase 1 Data Model: Runtime-State Corpus Cutover

This mission adds no new persistent entity. It changes **which existing store is authoritative** and
adds one bookkeeping marker. The entities below are the ones the cutover reads, writes, and reasons
about.

## Authority entities (existing — reused, not redefined)

### Reduced status snapshot (authority after cutover)
- **What**: the deterministic projection of `status.events.jsonl` (`reduce()` / `materialize_snapshot()`).
- **Runtime slots per WP**: `shell_pid`, `shell_pid_created_at`, `agent`, `assignee`, `tracker_refs`,
  `subtasks` (id → status), `review` (ReviewOverride).
- **Role change**: becomes the **sole** authority for these slots once the predicate is deleted (IC-03).
- **Access seam**: the `wp_snapshot_state` accessor (shipped #2817) — bypass readers reroute onto it.

### `InnerStateChanged` seed events + seed `planned→claimed` transition
- **What**: the events the backfill emits to reconstruct pre-eviction frontmatter/checkbox state.
- **Identity**: deterministic content-namespaced ULID (`mission_id|wp_id|field`) → idempotent re-runs.
- **Fold**: ordinary WP01 events; the reducer folds them into the snapshot with no special-casing.
- **Honesty bound (C-005)**: subtask-completion `at` is clamped (fictional); seed ULIDs are
  content-namespaced (not chronological). Valid only because no consumer reads subtask-completion time
  or relies on seed-ULID order.

### `LegacyWPRuntime` (old reader — verify ground truth)
- **What**: the pre-eviction frontmatter/checkbox per-WP view (`read_legacy_runtime`).
- **Role**: the value `verify_backfill` compares the snapshot against by **count + value** parity.
- **Lifecycle**: read-only; deleted from the code path once the fallbacks (IC-04) are gone.

## Cutover marker (the one stateful addition)

### `meta.json` `status_phase`
- **Type**: string/int; `>= 1` historically meant "snapshot authority active" (predicate `status_phase >= 1`).
- **Writer**: the cutover orchestration helper — **sole writer**, writes only **after** a passing verify
  (FR-003). No other production writer exists (confirmed by squad).
- **Readers**: `_phase1_snapshot_authority_active` (runtime-slot authority) — **deleted in IC-03**. BUT
  `_legacy_lane_mirror_enabled` (kept by C-004) — **still reads `status_phase`**. So after IC-03 the
  field remains a **live runtime gate for the lane mirror**, not an inert marker (corrected post-planning;
  see research D-02). Flipping `0 → 1` therefore also **activates the lane mirror** for that mission.
- **State transition**: `absent | null | "0"`  →(backfill+verify passes)→  `"1"`. No reverse transition
  in this mission. **IC-06 must NOT retire this field** (would disable the lane mirror corpus-wide).
- **Today's corpus state**: all 299 dogfood missions are `status_phase=0` → lane mirror OFF, runtime
  slots read from frontmatter. IC-01b flips this repo's corpus; IC-02 flips consumers' on upgrade.

## Deleted / inert model surfaces (end-state)

| Surface | Fate | Concern |
|---------|------|---------|
| `_phase1_snapshot_authority_active` (predicate) | **deleted** + facade alias/`__all__` dropped | IC-03 |
| `_legacy_lane_mirror_enabled` | **kept** (`lane` still frontmatter-authored) | C-004 (out of scope) |
| `workflow_cores.resolve_review_feedback_context` frontmatter fallback | **deleted** (one block w/ bypass reader) | IC-04 |
| `merge/done_bookkeeping._extract_done_evidence` frontmatter synthesis | **deleted** (after event-sourced replacement confirmed) | IC-04 |
| `tasks_move_task` `agent` ownership frontmatter read | **rerouted** to snapshot accessor | IC-04 |
| `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` (15 dead-symbol pins) | **removed** (library now has callers) | IC-01 |
| `_SANCTIONED_READER_MODULES` (#2093 tolerated set) | → `frozenset()` | IC-05 |
| inert `wp_metadata` fields + `WP_FIELD_ORDER` slots | **removed** (optional) | IC-06 |
| `- [ ] T###` markdown checkboxes (`tasks.md`/WP) | **removed** — subtask completion is snapshot-only (via `mark-status`); removed only after backfill seeds from them (C-010) | IC-10 |
| lane-transition guard checkbox parsing (`core/subtask_rows.py`) | **rerouted** to the snapshot `subtasks` slot | IC-10 |
| doctrine prompt templates instructing checkbox ticks | **updated** → direct agents to `mark-status` | IC-10 |

## Resolved runtime identity (event-sourced) vs authored recommendation (frontmatter)

Added by the 2026-07-20 operator decision (FR-012–FR-015). Two *distinct* representations of a WP's
role/profile/model, never conflated (C-008):

| | **Authored / recommended** | **Resolved / actual** |
|---|---|---|
| Meaning | who/what a WP was *designed* to run by | who/what *actually* resolved and ran it |
| Authority | frontmatter (static, `#2093` authored-intent) | event log → snapshot (dynamic, latest-wins) |
| Fields | authored `role`, `agent_profile`, `model` | resolved `role`, `agent_profile`(+`agent_profile_version`), `model`, `provider` |
| Written | once, at tasks-finalize | at each pick-up/claim/reassign transition |
| Lifecycle | fixed | **shifts** (implementer→reviewer, model swap) — the reason it must be event-sourced |
| Source of truth for the recorded value | n/a | `resolve_profile`/`resolved_agent()` / dispatch resolution — **never** the frontmatter string (C-007) |

**New event vocabulary (IC-08)** — NOT present today; to be added:
- `WPInnerStateDelta` (or the structured claim-transition `actor`) gains `role`, `agent_profile`,
  `agent_profile_version`, `model`, `provider`.
- reducer `_RUNTIME_SLOTS` + `_apply_annotation_delta` gain matching latest-wins slots.
- historical backfill does **not** seed authored frontmatter recommendations as resolved actuals; legacy
  WPs remain empty on the resolved side until a genuine resolver-backed runtime event exists.

**Reconstruction reader (IC-07)** — one `reconstruct_wp_view(feature_dir, wp_id)` replaces the three
hand-rolled gates (dashboard scanner, `agent tasks status` board, `WorkPackage`), assembling resolved
fields from the snapshot and authored fields from frontmatter (distinctly labeled).

**SaaS delivery (IC-09)** — the resolved actual rides the structured `actor` (`{role, profile, tool,
model}`) on the claim `StatusEvent`; `spec_kitty_events` 6.1.0 already accepts it.

## Invariants (acceptance-shaping)

- **INV-1 (fail-closed)**: `status_phase` is `"1"` for a mission **iff** that mission's backfill+verify
  passed. No mission is flipped on a mismatch. (SC-001, NFR-001)
- **INV-2 (single authority)**: after cutover, no code path reads WP runtime slots from frontmatter;
  every read resolves the snapshot. (FR-008, SC-003)
- **INV-3 (byte-stability)**: a runtime-state transition writes 0 bytes to `tasks/WP##.md`. (NFR-003, SC-004)
- **INV-4 (idempotency)**: re-running backfill (CLI or upgrade) seeds nothing and does not re-flip.
  (NFR-002)
- **INV-5 (no repo-root write)**: all event writes resolve via `canonicalize_feature_dir`; nothing lands
  at repo root. (C-003, #2815)
- **INV-6 (resolved from resolver, never frontmatter)**: a recorded resolved `agent_profile`/`role`/`model`
  originates from `resolve_profile`/`resolved_agent()` / dispatch resolution, never a copy of the
  frontmatter `agent_profile` string. (C-007, FR-013)
- **INV-7 (authored ≠ resolved)**: every WP-view consumer surfaces authored recommendation and resolved
  actual as distinct values; the reconstruction reader is the single assembly point. (C-008, FR-012, SC-007)
- **INV-8 (latest-actual wins)**: after multiple pick-ups, the reconstructed resolved identity equals the
  most recent transition's actual, with 0 bytes written to `tasks/WP##.md`. (FR-013, SC-008)
