# WP05 design note — run-index migration shape and legacy key (Q9)

**Decision id**: `01M1V8J842E7CJR6MGZ0MW3DQF` (slot `plan.wp05.run-index-migration`)
**Requirements**: FR-016, C-003, SC-006 · **Contract**: `contracts/run-state-store.md` §1 · **Data model**: `data-model.md` §8.1
**Decided by**: WP05 implementer (`python-pedro`), 2026-09-06

## Decision

**In-place rekey on first touch, keyed by `mission_id`; missions without a `mission_id` are keyed `legacy-<slug>`.**

The `feature-runs.json` key for a mission is `run_index_key(mission_slug, mission_id)`
(`src/runtime/next/runtime_bridge_io.py`):

| Mission has `mission_id`? | Key | Example |
|---|---|---|
| yes | the ULID itself | `01KTPKST…` |
| no | `legacy-<mission_slug>` | `legacy-042-test-mission` |

The bare slug is never a key. `mission_slug` is stored inside every entry as a display field.

### Migration shape

Every reader of the index (`get_or_start_run`, `_existing_run_ref`, `_resolve_run_dir_for_mission`)
loads it through `_load_run_index`, which applies `_canonicalize_run_index` in memory: each entry
is moved from a pre-WP05 slug key to `run_index_key(entry.mission_slug or key, entry.mission_id)`.
Only the index's single writer, `get_or_start_run`, persists the rekeyed index — and only when
something actually moved. The read-only resolvers (query mode, OperationalContext construction)
see the canonical view without touching the file, preserving their non-mutating contracts
(`test_query_mode_does_not_create_runtime_index_on_first_use`, NFR-004).

Properties, each pinned in `tests/runtime/test_run_state_hardening.py`:

- **Idempotent** — a second pass over a canonical index reports no change; two consecutive
  `get_or_start_run` calls leave the file byte-identical after the first.
- **Lossless** — every run survives; an entry whose canonical slot is already occupied stays under
  its old key rather than overwriting the occupant (a bare-slug key is inert for lookups, so a
  retained one can never be resolved by a different mission).
- **Identity-correct** — a slug-keyed entry is adopted by a caller only when their canonical keys
  agree. A stored `mission_id` that differs from the caller's is another mission's run and is
  rekeyed under *its own* ULID (SC-006a: the collision test asserts both ULIDs end up as keys).
  A stored entry with no `mission_id` is adoptable only by a caller that also has none — a
  backfilled mission (`spec-kitty migrate backfill-identity`) starts a fresh run rather than
  inheriting a slug-matched cursor of unknown provenance; the legacy entry is retained under
  `legacy-<slug>` for the operator to reconcile.

## Rationale

- **Why in-place on first touch, not a one-shot migrate command.** There is no upgrade hook that
  runs before `spec-kitty next`; an operator upgrading mid-mission would otherwise hit a stale
  slug-keyed index on the very first call. Rekeying on touch closes the defect class by
  construction (charter Standing Order #5): there is no window in which a slug-keyed lookup can
  still happen, because no slug-keyed lookup exists any more. A one-shot migration would also
  need its own error surface and a doctor check to notice it never ran.
- **Why `legacy-<slug>`.** It is the precedent the three transactional status doors already use
  for the lock key of a mission without a ULID (`coordination/status_transition.py:1360/:1543/:1606`),
  so an operator sees one legacy-key convention across the status lock and the run index, and the
  prefix makes a legacy entry visually distinct from a ULID in the file.
- **Why readers do not persist.** `_existing_run_ref` backs fresh query mode, whose contract is
  "non-mutating for the project working tree and `feature-runs.json`"; `_resolve_run_dir_for_mission`
  is used while building an OperationalContext at claim sites (NFR-004: no run-start side
  effects). Persisting from either would silently turn a read into a write.

## Alternatives considered

| Alternative | Why not |
|---|---|
| One-shot `spec-kitty migrate rekey-run-index` | Needs a hook before first use, a doctor check, and leaves the slug lookup alive until it runs. |
| Key legacy missions by bare slug (no prefix) | Keeps the bare slug as a live key — the exact C-003 violation this WP closes — and makes a legacy entry indistinguishable from a pre-WP05 one. |
| Adopt a `mission_id`-less slug entry for a caller that has a `mission_id` | Re-opens the SC-006 collision for the legacy case (mission A without ULID, deleted; mission B same slug with ULID inherits A's cursor). |
| Persist the rekey from every reader | Breaks the non-mutating contracts of query mode and OC construction. |

## Related hardening landed with this decision

- **Loud missing-state (FR-016)** — `RunStateMissing(MissionRuntimeError)` (`error_code`
  `RUN_STATE_MISSING`, carries `mission_id`, `mission_slug`, `run_id`, `run_dir`) is raised by both
  `get_or_start_run` and `_existing_run_ref` when a live entry's `state.json` is gone; the old
  fall-through to "start a new run" is removed. Query mode raises too: previewing a phantom fresh
  run over orphaned history is the same defect wearing a read-only hat.
- **Atomic cursor (FR-015)** — `_write_snapshot` stages `state.json.tmp` in the run directory,
  fsyncs, then `os.replace`s; `_append_event` writes the whole journal line in one `write()` and
  fsyncs.
- **Pure progress read (FR-017)** — `decision._compute_wp_progress` calls `materialize_snapshot`
  and logs (never swallows) a failed weighted-progress computation.
