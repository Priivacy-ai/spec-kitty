# Implementation Plan: Evict WP runtime state into the event log

**Branch**: `mission-prep/2684-wp-runtime-state-eviction` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/wp-runtime-state-eviction-01KXWN13/spec.md`

## Summary

Evict all runtime-mutable WP state (`shell_pid`(+baseline), subtask completion, `## Activity Log`
notes, `tracker_refs`, `agent`/`assignee`, review-cycle fields) out of `tasks/WP##.md` and the
`tasks.md` subtask surface into the canonical append-only event log, via **one generic
`InnerStateChanged` off-axis event** folded into the reduced snapshot (design of record:
[ADR 2026-07-19-1](../../docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md)).
The WP files become static design-intent only, which stabilises the dossier content hash (AC-5), makes
subtask completion event-sourced (the merged P0 red test flips green), and lets claim-liveness resolve
from the snapshot. Additionally fixes the false-force provenance bug (FR-015). Executed as a
**brownfield migration** under the strict `backfill → verify → reader cutover → writer cutover → delete
fallbacks` ordering, with **extreme-campsiting** removal of the dead tails the eviction creates.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: `typer` (CLI), `pydantic` (models), internal `specify_cli.status` (event
log / reducer / FSM), `specify_cli.coordination` (transactional writes), `specify_cli.migration`
(frontmatter stripper), `specify_cli.doctrine`
**Storage**: append-only `status.events.jsonl` (SSOT for runtime state) + the reduced snapshot;
git-backed WP markdown carries **static design-intent only** after cutover
**Testing**: `pytest` (`pytest.ini` marker registry). New coverage: an architectural invariant test
(#2093), a proof-of-drive lifecycle hash test (AC-5), a persisted-force command-layer test (FR-015)
plus re-pointed existing force tests, a migration idempotency + fail-closed-verify test, and the
already-merged regression `test_issue_2684_subtask_completion_event_sourced.py`. Markers:
`regression`, `integration`, `git_repo`, `architectural`, `unit`
**Target Platform**: Linux/macOS CLI (`spec-kitty-cli`)
**Project Type**: single (Python CLI library under `src/specify_cli/`)
**Performance Goals**: the reducer fold is **O(events) with no additional re-reduction pass**
(NFR-005 — asserted structurally, not by wall-clock)
**Constraints**: strict migration ordering incl. the symmetric-window closure (C-001); typed
`WPInnerStateDelta`, never a free dict (C-002); every emit site resolves `destination_ref` from stored
topology, never `Path.cwd()` (C-003 / #2647); the 9-lane FSM 27-pair matrix is not modified (C-004);
no field is dual-homed static+dynamic (#2093)
**Scale/Scope**: ~12 source modules across `status/`, `cli/commands/agent/`, `migration/`, `review/`,
`merge/`, `frontmatter.py`, plus a backfill migration over the live mission corpus

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter policy headline: **"Single canonical authority — every rule, surface, and identity has exactly
one source."** This mission is a *direct expression* of that policy: runtime state gets one authority
(the event log), static intent keeps one authority (the frontmatter). **PASS** — no violation; the
mission strengthens the invariant, enforced by the FR-013 refactor-stable architectural test.
Post-design re-check: the only transient two-authority state is the **bounded** C-001 migration window,
which the revised decomposition minimises via per-field atomic switch and tears down under IC-07 with
the no-dual-home assertion. **PASS.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/wp-runtime-state-eviction-01KXWN13/
├── plan.md · research.md · data-model.md · quickstart.md · contracts/ · tasks.md (Phase 2, not here)
```

### Source Code (repository root)

```
src/specify_cli/
├── status/
│   ├── models.py            # StatusEvent + policy_metadata; NEW InnerStateChanged + WPInnerStateDelta
│   ├── store.py             # read_events / is_non_lane_event / from_dict — surface annotations to reduce()
│   ├── reducer.py           # branch on kind; preserve slots; claim-transition policy_metadata fold
│   ├── wp_state.py          # sanctioned non-transition annotate() path (no matrix change)
│   ├── transitions.py       # validate_transition (unchanged matrix)
│   └── emit.py              # _infer_subtasks_complete → snapshot; emit sites resolve topology target
├── cli/commands/agent/
│   ├── tasks_transition_core.py   # _guard_subtasks → snapshot; build_transition_plan force fix (FR-015)
│   ├── tasks_shared.py            # _check_unchecked_subtasks (reader re-point)
│   ├── tasks_move_task.py         # cut god-write + tails (_mt_persist_tracker_refs, _mt_*uncheck*, _mt_clear_rollback_claim_markers)
│   ├── tasks_mark_status.py       # emit subtask InnerStateChanged (stop writing tasks.md checkbox)
│   ├── tasks_materialization.py   # review_artifact_override_* write half + coord mirror collapse
│   ├── implement.py               # :1730 shell_pid writer (this mission OWNS the restructuring, FR-014)
│   └── workflow_executor.py       # :695,:1370 shell_pid writers
├── migration/strip_frontmatter.py # MUTABLE_FIELDS extend + backfill engine
├── review/artifacts.py            # review_artifact_override_* READ half (FR-009 both-halves)
├── merge/done_bookkeeping.py      # legacy done-evidence fallback (delete after backfill)
├── frontmatter.py                 # write_shell_pid_claim* + __all__ (delete tail); add_history_entry + __all__ (delete)
├── core/stale_detection.py        # :402-403 claim-liveness reader re-point
├── task_utils/support.py          # WorkPackage.{shell_pid,agent,assignee} reader re-point
├── status/wp_metadata.py          # WPMetadata coercion; inert-field cleanup (deferred IC-08)
└── orchestrator_api/commands.py   # :1563 external Activity-Log writer (cross-package; own concern)

tests/
├── regression/ (test_issue_2684_*; force-provenance persisted) · architectural/ (#2093 invariant;
│   no_dead_symbols reconcile) · integration/ (proof-of-drive hash; migration idempotency + fail-closed)
│   · unit/ (fold ordering/preserve; delta merge rules)
```

**Structure Decision**: Single Python CLI project; in-place edits to `src/specify_cli/` + a net-new
backfill migration + the test surfaces above.

## Complexity Tracking

*No Charter Check violations — the mission reduces complexity (removes a split-brain). Table omitted.*

## Decomposition strategy (post-plan squad adjudication)

C-001 mandates **per-field** atomicity (a field's reader and writer must switch together, or dual-write
during a bounded window). The squad flagged that a horizontal reader-phase/writer-phase split is
orthogonal to that safety axis. **Decision: per-field vertical slices with an atomic reader↔writer
switch are the primary strategy** — no transient dual-authority window — with dual-write allowed only
where a field cannot switch atomically, explicitly bounded and torn down in IC-07 (charter
single-authority; close-by-construction). The field-eviction concerns below are therefore **vertical**
(each carries its reader re-point, authority-activation gated on that field's verified backfill, writer
cut, and created-orphan deletes). **Lane sizing: 2–3 lanes** — this mission is critical-path-bound
(IC-01 foundation, the field verticals, IC-07 closeout), not width-bound; sustained parallel width ≈ 2.

## Implementation Concern Map

> Concerns are architectural areas, **not** work packages. `/spec-kitty.tasks` translates these into
> WPs. Sequencing is expressed as concern dependencies to honour the brownfield migration contract.

### IC-01 — Off-axis event class + reducer fold foundation

- **Purpose**: The single generic `InnerStateChanged` event + typed `WPInnerStateDelta`, made visible to
  and correctly folded by the reducer, with the snapshot slot set that every field vertical reads.
- **Relevant requirements**: FR-001, FR-002, FR-004 (fold half), C-002, C-004; NFR-005.
- **Affected surfaces**: `status/models.py`, `status/store.py` (`read_events`/`is_non_lane_event`/
  `from_dict`), `status/reducer.py` (`_wp_state_from_event`), `status/wp_state.py` (annotate path).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: reducer today rebuilds the per-WP dict (carries only `force_count`) → must **preserve**
  untouched slots; wire discriminator must not collide with the `event_type` skip; **event-kind
  partition** fold (not `at`-interleave); an annotation must never be reduced as a lane transition
  (arch test). **Snapshot slot set is `{shell_pid, shell_pid_created_at, subtasks, notes, tracker_refs,
  agent, assignee, review}`** — includes `agent`/`assignee` and a `review` slot (squad HIGH: the
  authority table asserted these with no carrier). **The `planned→claimed` transition MUST extract
  `shell_pid`/`shell_pid_created_at`/`agent` from its `policy_metadata` into the snapshot slots**
  (squad HIGH: FR-004's claim path was otherwise unowned — the reducer reads `policy_metadata` nowhere
  today).

### IC-02 — Force-provenance fix (FR-015) — LAND FIRST

- **Purpose**: Stop stamping false `force` on evidence-gated review-rejection backward edges; pin at the
  persisted-event layer. Sequenced first so the field verticals rebase onto corrected force logic
  instead of racing it on shared files.
- **Relevant requirements**: FR-015; SC-007.
- **Affected surfaces**: `tasks_transition_core.py:218-219` (`build_transition_plan`),
  `tasks_move_task.py::_mt_emit_transitions`, `status/emit.py`.
- **Sequencing/depends-on**: none. **Code-collision edges (land first to avoid races)**:
  `tasks_transition_core.py` (with IC-04b), `tasks_move_task.py` + `status/emit.py` (with IC-04a/b/d).
- **Risks**: ask the FSM (`validate_transition` legal force-free), not a frozen edge list; **re-point**
  the enumerated existing plan-level tests (not delete); assert the **persisted** `StatusEvent.force`
  via the real move-task path with a genuine-force positive control.

### IC-03 — Migration engine: per-field backfill + fail-closed verify

- **Purpose**: Seed existing missions' frontmatter/checkbox state into the log idempotently; gate each
  field vertical's authority activation on verified parity.
- **Relevant requirements**: FR-010 (field-moves), FR-011; SC-006, NFR-002.
- **Affected surfaces**: `migration/strip_frontmatter.py` (extend `MUTABLE_FIELDS`, move `history` out of
  `STATIC_FIELDS`, retire `progress`), net-new backfill/seed-event module, read-back verify.
- **Sequencing/depends-on**: IC-01.
- **Risks**: deterministic namespaced ULIDs ordering **after** the annotated transition at equal `at`;
  **verify is fail-closed and aborts before any field's reader authority activates**; honest
  timestamp-clamp bound; zero-reader verification precedes deletions.

### IC-04 — Per-field eviction verticals (fan out to WPs by field)

Each vertical = reader re-point (behind flag) → **authority activation gated on this field's IC-03
verify** → writer cut → created-orphan deletes, **atomic per field** (C-001). FR-004/006/007/008/014;
SC-001, SC-005, SC-008.

- **IC-04a `shell_pid`(+baseline, +`agent` claim)** — readers `stale_detection.py:402-403`,
  `WorkPackage.shell_pid`; writers `implement.py:1730` (**owns the FR-014 restructuring**),
  `workflow_executor.py:695,:1370`, `tasks_move_task.py:1770`; **tails**: `frontmatter.py::
  write_shell_pid_claim*` (`:357-408`) + `__all__:448-449` + orphaned tests
  (`test_shell_pid_claim_baseline.py`, `test_implement_runtime_frontmatter_claim.py`,
  `test_tasks_move_task_authority_staging.py`), and **`_mt_clear_rollback_claim_markers`**
  (`tasks_move_task.py:1730`, sole caller is the god-write — a same-cut orphan, moved here from IC-08).
- **IC-04b `subtasks`** — gate re-source `_guard_subtasks` + `_infer_subtasks_complete` to snapshot;
  emit via `mark-status`; cut the god-write `_mt_persist_wp_file` + the `_mt_*uncheck*` trio. **Makes
  the merged red test green.**
- **IC-04c `tracker_refs`** — union delta (`map-requirements`, `move-task`); **strike from
  `WP_FIELD_ORDER`** (no #2093 dual-home); delete `_mt_persist_tracker_refs` (`:1707-1727`).
- **IC-04d `notes`/Activity Log** — append delta from the **full write-seam census (≥7)**: the six
  `append_activity_log` writers **plus** the divergent frontmatter seam
  `task_metadata_validation.py:146-165` (an eviction target, not optional cleanup).
- **IC-04e `agent`/`assignee`** — `agent` rides the claim `policy_metadata` (IC-01); `assignee` via
  `InnerStateChanged`; re-point `WorkPackage.{agent,assignee}` + `WPMetadata`.
- **orchestrator_api sub-concern** — `orchestrator_api/commands.py:1563` is a **cross-package** writer
  (ACL boundary); carve as its own WP with **SC-008** (#2647 topology-resolution, not `Path.cwd()`) as
  its dedicated acceptance evidence.
- **Sequencing/depends-on**: IC-01, IC-02 (landed first), and each field's IC-03 verify.
- **Risks**: every new emit site resolves `destination_ref` from stored topology (C-003/SC-008); **no
  inbound gate from PR #2766 — #2766 rebases onto this mission's writer cutover** (C-006), not the reverse.

### IC-05 — Review-cycle eviction (both halves)

- **Purpose**: Event-source `review_artifact_override_*` as a matched write+read pair without breaking
  the merge gate; land the `review` snapshot slot.
- **Relevant requirements**: FR-009.
- **Affected surfaces**: `tasks_materialization.py` (write + `_persist_review_artifact_override_in_coord`
  mirror collapse), `review/artifacts.py` (read half), the merge-gate override recognition.
- **Sequencing/depends-on**: **IC-01** (needs the `review` snapshot slot + fold — squad HIGH: otherwise
  a second read path = #2093 violation) **and** IC-03 (fallback deletes gated on backfill).
- **Risks**: write-only eviction silently breaks override recognition → false merge blocks; the review
  read authority is the reduced snapshot, not a parallel event read.

### IC-06 — `history[]` / `progress` deprecation (single owner)

- **Purpose**: One deprecation unit end to end — no half-owned dead writer.
- **Relevant requirements**: FR-010.
- **Affected surfaces**: `migration/strip_frontmatter.py` (field-move + retire `progress`);
  `frontmatter.py::add_history_entry` (`:176,:347`) **+ `__all__:445`**; **`test_no_dead_symbols.py:282`
  allowlist entry**; zero-reader verification for both `history[]` and `progress`.
- **Sequencing/depends-on**: IC-03 (after backfill/zero-reader verify).
- **Risks**: delete the symbol **and** its `__all__`/allowlist entry together (no stub that masks the
  next dead symbol).

### IC-07 — Delete legacy fallbacks + land invariants (closeout)

- **Purpose**: Remove the frontmatter fallbacks and any dual-write shim; land the enforcing guards.
- **Relevant requirements**: FR-009 (deletes), FR-013; NFR-001, AC-5.
- **Affected surfaces**: the FR-005 fallback-flag removal, any C-001 dual-write shim teardown,
  `workflow_cores.py:340-348` + `done_bookkeeping.py:104-105` fallback deletion (gated on backfill), the
  AC-5 stable-hash guard, the #2093 refactor-stable architectural test (incl. no-field-in-both-columns).
- **Sequencing/depends-on**: IC-04 (all field verticals) + IC-05 + IC-06.
- **Risks**: no inert fallback / no dual-write shim left behind; hash guard covers the full driven
  lifecycle (proof-of-drive).

### IC-08 — Deferred post-cutover reduction (migration-gated reader surfaces only)

- **Purpose**: Remove code that is only *inert after* the corpus migration — narrowed to genuinely
  migration-gated reader/coercion surfaces (the created-orphan writer helpers moved to IC-04).
- **Relevant requirements**: (campsiting, no new FR).
- **Affected surfaces**: `wp_metadata.py` inert fields + `coerce_shell_pid` (`:363`) + `reviewer_shell_pid`
  (`:270`), `WP_FIELD_ORDER` cosmetic slots.
- **Sequencing/depends-on**: IC-07 (migration complete).
- **Risks**: pulling these forward would clobber legacy on-disk WPs mid-migration — do NOT reorder; if
  it grows past a bounded reduction, split into a separate post-cutover mission (not this one).

## Post-plan adversarial review (2026-07-19)

Four profile-loaded lenses (paula-patterns, planner-priti, architect-alphonso, randy-reducer) reviewed
this plan; verdicts ranged revise / conditional-go / approve-with-fixes. Convergent amendments folded in
above:

- **Decomposition axis (paula CRITICAL + planner + architect)** → committed to **per-field vertical
  slices, atomic switch** (Decomposition-strategy section); dual-write only as a bounded IC-07-torn-down
  fallback.
- **Structural verify gate (planner + paula HIGH)** → each field vertical's authority activation depends
  on its IC-03 fail-closed verify (no reader authority before verify).
- **IC-04 over-bundle (planner + paula HIGH)** → pre-split into per-field verticals IC-04a–e + the
  orchestrator_api sub-concern.
- **Land IC-06→now IC-02 first (planner HIGH + paula)** → force-fix sequenced first with its
  code-collision edges drawn.
- **Carrier gaps (architect HIGH×2)** → `agent`/`assignee` + `review` snapshot slots added; the
  `planned→claimed` `policy_metadata`→snapshot fold made explicit in IC-01.
- **Review read authority (paula HIGH)** → IC-05 depends on IC-01 for a `review` snapshot slot (no
  parallel read path).
- **Campsiting tails (randy HIGH/MEDIUM)** → `_mt_clear_rollback_claim_markers` moved to IC-04a;
  `add_history_entry` + `__all__` + allowlist assigned to IC-06; `write_shell_pid_claim*` `__all__` +
  orphaned tests assigned to IC-04a; activity-log census corrected to ≥7 seams (IC-04d).
- **PR #2766 direction (planner)** → no inbound gate; it rebases onto us (IC-04 risks).
- **Lane sizing (planner)** → 2–3 lanes; critical-path-bound.

Contract/data-model fidelity fixes (emit-force table labelled illustrative-not-implementation; claim
`policy_metadata` fold + `agent`/`assignee`/`review` slots) are applied in `data-model.md` and
`contracts/`. IC-08's deferral was affirmed correct by both randy and paula (no over-reach into the
clobber window).
