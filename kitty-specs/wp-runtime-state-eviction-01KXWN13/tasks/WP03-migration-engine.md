---
work_package_id: WP03
title: 'Migration engine: backfill + fail-closed verify'
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-opus-4-8
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/
create_intent:
- src/specify_cli/migration/backfill_runtime_state.py
- tests/integration/test_migration_backfill.py
- tests/unit/migration/test_backfill_runtime_state.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/strip_frontmatter.py
- src/specify_cli/migration/backfill_runtime_state.py
- tests/integration/test_migration_backfill.py
- tests/unit/migration/**
role: implementer
tags: []
shell_pid: "2517029"
shell_pid_created_at: "1784459594.4"
---

# WP03 — Migration engine: backfill + fail-closed verify

## ⚡ Do This First: Load Agent Profile

Before reading further, run `/ad-hoc-profile-load python-pedro` and adopt the profile: its identity
(type-safe Python 3.12+ implementer), its directives (TDD red→green→refactor, type hints on public
APIs, the full `pytest`/`ruff`/`mypy` gate before handoff), its tactics (`pathlib`, deterministic
helpers, dataclass results), and its **boundaries** — the migration **ordering** and the fail-closed
verify contract are ratified in the design of record. Do not reorder the phases, do not delete the
legacy fallbacks (WP10 owns those deletes), and do not weaken the fail-closed abort into a warning.

## Objective

Build the migration engine that seeds the live mission corpus into the event log safely and gates every
field vertical's authority activation on **verified parity**. Extend the canonical
`strip_frontmatter.py:MUTABLE_FIELDS` (add `shell_pid_created_at`, `review_artifact_override_*`,
`reviewer_shell_pid`, and `history`; move `history` **out** of `STATIC_FIELDS` **and into**
`MUTABLE_FIELDS` so the corpus strip actually removes it — mirroring `progress`; retire `progress`),
ship a net-new
`backfill_runtime_state.py` that reconstructs each WP's frontmatter/checkbox runtime state as seed
`transition` + `InnerStateChanged` events with **deterministic namespaced ULIDs** ordered *after* the
annotated transition at equal `at`, and implement a **fail-closed verify** that aborts before any
reader cutover if the reduced snapshot does not match the OLD frontmatter/checkbox reader by count +
value. Add zero-reader verification for `history[]`/`progress` and idempotency + fail-closed tests. This
WP is P1: it gates cutovers for every downstream field vertical (WP05–WP09) and its fallback-delete is
handed to WP10.

## Context

**Design of record**: ADR `docs/adr/3.x/2026-07-19-1-...innerstatechanged.md`. This WP realises
**IC-03** (migration engine: per-field backfill + fail-closed verify) and the `MUTABLE_FIELDS`
extension of **IC-06** from `plan.md`. Contract of record: `contracts/migration.md`.

**Requirements owned here**: FR-010 (extend `MUTABLE_FIELDS`, move `history`, retire `progress`,
zero-reader verification), FR-011 (backfill → verify(fail-closed) → … ordering; deterministic
namespaced ULIDs; idempotency; honesty clamp). Success criterion **SC-006** (N>0 first run, 0 second
run, corrupt seed aborts before cutover) and **NFR-002** (idempotent, 100% count+value parity).

**Design-of-record facts you must honour** (see `contracts/migration.md`):

- **Strict order**: `backfill → verify(pre-strip, FAIL-CLOSED) → reader cutover → writer cutover →
  strip mutable fields → delete fallbacks → land hash guard`. This WP owns **backfill + verify + the
  `MUTABLE_FIELDS` field-moves**; it does **not** perform reader/writer cutover (the field verticals do)
  and does **not** delete the legacy fallbacks (WP10 does, gated on this backfill).
- **Verify runs against the UN-stripped frontmatter.** `verify` MUST compare the reduced snapshot
  against the OLD frontmatter/checkbox reader reading the **un-stripped** frontmatter (or an
  independently reconstructed legacy value) — the strip (`strip_mutable_fields`) MUST NOT run before
  `verify`. If the strip runs first, the old reader reads empty frontmatter → vacuous parity → a false
  green that masks a real mismatch. The pinned sequence is `backfill → verify(pre-strip) → cutover →
  strip`; never `strip → verify`.
- **Deterministic namespaced ULIDs.** Seed `event_id` = a content-namespaced ULID
  (`mission_id + wp_id + field`), idempotent (a re-run seeds nothing). The seed ULID MUST order
  **after** the `claimed` transition it annotates at equal `at` (FR-002 partition; the WP01 reducer
  folds annotations after transitions, but the id must still sort deterministically).
- **Clamp honesty.** Subtask checkboxes carry no timestamp → the backfilled mark clamps `at` to the
  WP's `claimed` timestamp (fictional time). "No data loss" is asserted against **count + value**
  parity of the reduced snapshot, NOT temporal fidelity, and holds only because no consumer reads
  subtask-completion time or relies on seed-ULID chronological order — **assert this precondition**.
- **Fail-closed verify.** The verify asserts the reduced snapshot equals what the OLD frontmatter/
  checkbox reader produces, by count + value. Any mismatch — including a fault-injected corrupt seed —
  MUST **abort before reader cutover**. Not a warning; an abort.
- **Zero-reader checks precede deletion.** `history[]` and `progress` are deleted outright only after a
  zero-reader verification proves no live reader anywhere (not merely no authority-read).

### Current wiring (grounded)

- `strip_frontmatter.py:23-34` — `MUTABLE_FIELDS` frozenset: `lane`, `review_status`, `reviewed_by`,
  `review_feedback`, `progress`, `shell_pid`, `assignee`, `agent`. (`progress` is already at `:29`.)
- `strip_frontmatter.py:37-58` — `STATIC_FIELDS` frozenset; `history` is the last member at `:56`.
  `STATIC_FIELDS` is documentation/allowlist only — the stripper is driven purely by `MUTABLE_FIELDS`.
- `strip_frontmatter.py:79` — `strip_mutable_fields(feature_dir) -> StripResult`; iterates
  `tasks/WP*.md` (`:110`), records `lane` (`:125-126`), deletes each `MUTABLE_FIELDS` key
  (`:130-133`), writes back via `FrontmatterManager` (`:136`), then strips `tasks.md` frontmatter
  (`:147-166`). `StripResult` at `:61-76`.
- **Determinism precedents to reuse (do not fork):** `migration/mission_state.py:473-482`
  `deterministic_ulid(seed) -> str` (sha256 → 16 bytes → 26-char Crockford base32); the identical
  algorithm lives at `migration/rebuild_state.py:66` `_deterministic_id(*parts)`. Random-ULID
  precedent is `status/emit.py:113` `_generate_ulid()` — but seeds must be **deterministic**, so use
  `deterministic_ulid` with stable seed parts (e.g. `mission_id, wp_id, field, from_lane, to_lane`).
- **Event seeding seam:** construct `StatusEvent`/`InnerStateChanged` (from `status.models`) and append
  via `status/store.py` — `append_events_atomic_verified` (`store.py:382-395`, tmp + `os.replace` +
  readback verify) is the durability-guaranteed batch path; `append_event_verified` (`:328-338`) for
  single events. `EVENTS_FILENAME = "status.events.jsonl"` (`store.py:38`). Note `rebuild_state.py`
  writes raw-dict JSONL directly (`:758-766`) — prefer the typed `StatusEvent`/store path here for the
  WP01 annotation decoder to read it back cleanly.
- **Idempotent-backfill precedents to model the module on:** `backfill_identity.py:99`
  `backfill_mission(feature_dir, *, dry_run=False) -> BackfillResult` (never overwrites; canonical
  sorted-key write); `backfill_topology.py:139` `backfill_mission_topology(...)` (never overwrites;
  fail-closed against phantom branches); `rebuild_state.py:539` `rebuild_event_log(...)` (event-seeding
  with `_deterministic_id`, `BackfillAction = Literal["wrote","skip","error"]`). Mirror the
  `BackfillResult` dataclass + `dry_run` + repo-walk shape.
- **Legacy fallback readers (T013 zero-reader targets; do NOT delete — WP10 does):**
  `workflow_cores.py:328-348` `resolve_review_feedback_context` reads frontmatter `review_status`
  (`:340`) / `review_feedback` (`:341`), returning a `"frontmatter"` source when `review_status ==
  "has_feedback"` (`:342-346`); `_extract_done_evidence` at **`src/specify_cli/merge/done_bookkeeping.py:95`**
  (`:95-113`, note the `merge/` subtree — **not** a top-level `done_bookkeeping.py`) reads
  `meta.reviewed_by` (`:104`) / `meta.review_status` (`:105`), synthesising `DoneEvidence` when
  approved. Both read exactly the fields `MUTABLE_FIELDS` strips — once stripped + backfilled they
  become permanently-empty (zero-reader) paths.

### Subtask T010: Extend `MUTABLE_FIELDS` (incl. `history`); move `history` out of `STATIC_FIELDS`; retire `progress`

**Purpose**: Reclassify the newly-evicted fields in the canonical stripper so a corpus strip removes
them from frontmatter, without forking the field registry.

**Steps**:
1. In `src/specify_cli/migration/strip_frontmatter.py`, extend `MUTABLE_FIELDS` (`:23-34`) with
   `shell_pid_created_at`, the `review_artifact_override_*` field name(s) (enumerate the concrete keys
   — mirror the exact frontmatter key names the write half in `tasks_materialization.py` used),
   `reviewer_shell_pid`, **and `history`**. Do **not** fork the set; extend it in place.
2. Move `history` **out** of `STATIC_FIELDS` (`:56`) **and add it to `MUTABLE_FIELDS`** (step 1) — the
   two moves are a pair. `STATIC_FIELDS` is documentation/allowlist only; the stripper is driven purely
   by `MUTABLE_FIELDS`, so removing `history` from `STATIC_FIELDS` **without** adding it to
   `MUTABLE_FIELDS` leaves the field orphaned in frontmatter (the stripper never removes it — the exact
   strip gap this fixes). Adding `history` to `MUTABLE_FIELDS` alongside `shell_pid_created_at`/
   `review_artifact_override_*`/`reviewer_shell_pid` makes the corpus strip remove it, mirroring how
   `progress` is stripped. Per FR-010 `history[]` is dead and mis-filed; this WP only *reclassifies +
   strips* it — the actual outright deletion of the `history[]` field and its writer `add_history_entry`
   is **WP07/T028** territory, not here.
3. `progress` is already in `MUTABLE_FIELDS` (`:29`); FR-010 says **retire `progress` explicitly, do
   not silently drop**. Add a comment/marker (or a dedicated retired-fields note) documenting the
   retirement so a reader knows it was deliberate, and ensure the strip removes it (it already does via
   `MUTABLE_FIELDS` membership).
4. Keep `strip_mutable_fields` (`:79`) mechanics unchanged — you are extending the field sets it
   consumes, not rewriting the stripper.

**Files**: `src/specify_cli/migration/strip_frontmatter.py`.

**Validation checklist**:
- [ ] `MUTABLE_FIELDS` contains `shell_pid_created_at`, `review_artifact_override_*`,
      `reviewer_shell_pid`, **and `history`** (and still `progress`, `shell_pid`, `agent`, `assignee`,
      review fields).
- [ ] `history` is no longer in `STATIC_FIELDS` **and IS in `MUTABLE_FIELDS`** (both halves of the move).
- [ ] A strip over a fixture WP removes the newly-added mutable keys — **including `history`** — and
      leaves static intent intact (assert the stripped frontmatter has no `history` key).

**Edge cases**: a WP missing a given mutable key strips cleanly (no `KeyError`); `review_artifact_
override_*` may be multiple concrete keys — enumerate all, do not glob-guess.

### Subtask T011: Backfill module — seed transition + `InnerStateChanged`; deterministic ULIDs; clamp

**Purpose**: The engine that reconstructs runtime state from existing frontmatter/checkboxes into seed
events, idempotently and deterministically.

**Steps**:
1. Create `src/specify_cli/migration/backfill_runtime_state.py`. Model the public shape on
   `backfill_identity.py:99`/`backfill_topology.py:139`: a per-mission
   `backfill_runtime_state(feature_dir, *, dry_run=False) -> BackfillResult` and a repo walker
   `backfill_runtime_state_repo(repo_root, *, dry_run=False, mission_slug=None) -> list[BackfillResult]`.
   Reuse a `BackfillResult` dataclass with an action enum (`Literal["wrote","skip","error"]` per
   `rebuild_state.py:63`).
2. For each WP in the corpus, read the pre-eviction frontmatter/checkbox runtime state (the fields
   about to be stripped: `shell_pid`/`shell_pid_created_at`/`agent`/`assignee`/subtask checkboxes/
   `tracker_refs`/`review_artifact_override_*`) and reconstruct events:
   - the **claim** state rides a seed `planned→claimed` `StatusEvent` with `policy_metadata` carrying
     `shell_pid`/`shell_pid_created_at`/`agent` (WP01 reducer folds these into slots);
   - subtask completion, `assignee`, `tracker_refs`, notes, and `review` ride seed `InnerStateChanged`
     annotations with the appropriate typed delta.
3. Mint seed `event_id`s via `deterministic_ulid` (`mission_state.py:473`) with stable seed parts
   (`mission_id + wp_id + field` at minimum; include `from_lane`/`to_lane` for transitions). Ensure the
   annotation seed id sorts **after** the transition it annotates at equal `at` (append a namespaced
   suffix/tag so the deterministic bytes order later; the WP01 partition already folds annotations
   after transitions, but keep the id ordering deterministic).
4. **Clamp** backfilled subtask-completion `at` to the WP's `claimed` timestamp (fictional time).
   Document the clamp at the call site.
5. Persist via the typed store seam `append_events_atomic_verified` (`store.py:382-395`). **Idempotent**:
   before appending, check whether a seed with that deterministic id already exists in
   `status.events.jsonl`; if so, skip (a re-run seeds nothing — NFR-002). Resolve the write target from
   the feature dir / stored topology, never `Path.cwd()` (C-003).

**Files**: `src/specify_cli/migration/backfill_runtime_state.py` (new).

**Validation checklist**:
- [ ] First run over a fixture with evictable state seeds N>0 events; the reduced snapshot equals the
      OLD reader's snapshot by count+value.
- [ ] Second run seeds 0 (idempotent).
- [ ] Seed ids are byte-identical across runs (deterministic).
- [ ] Claim state materialises into the snapshot `shell_pid`/`agent` slots via the seed transition's
      `policy_metadata`.
- [ ] Subtask seed `at` equals the WP's `claimed`.

**Edge cases**: a WP with no evictable state seeds nothing; a WP `claimed`-less (never claimed) → no
clamp anchor, so subtask marks (if any) need a defined fallback anchor — decide and document (prefer:
skip subtask seed for a never-claimed WP, since it cannot have completed subtasks); a partially-migrated
corpus (some seeds present) seeds only the missing ones.

### Subtask T012: Fail-closed verify (count+value parity vs old reader; abort before cutover)

**Purpose**: The gate. Prove the reduced snapshot equals the OLD frontmatter/checkbox reader before any
field's reader authority activates; abort on any mismatch or fault-injected corruption.

**Steps**:
1. In `backfill_runtime_state.py`, add `verify_backfill(feature_dir) -> VerifyResult` (fail-closed):
   materialise the WP01 reduced snapshot and compare, per WP and per field, against the value the OLD
   frontmatter/checkbox reader produces (the pre-eviction read path). Compare by **count** (same number
   of WPs/subtasks/notes/tracker_refs) **and value** (each slot equals the legacy-derived value).
   **Verify against the UN-stripped frontmatter.** The old frontmatter/checkbox reader in this compare
   MUST read the **un-stripped** frontmatter (or an independently reconstructed legacy value). Do
   **not** run `strip_mutable_fields` before `verify` — if the strip runs first the old reader reads
   empty frontmatter and every field trivially "matches" empty → **vacuous parity → false green** that
   masks a real backfill mismatch. Enforce the pinned order `backfill → verify(pre-strip) → cutover →
   strip`; the strip is a *downstream* step, never a precondition of verify.
2. On **any** mismatch, raise/return a fail-closed result that **aborts before reader cutover** — the
   caller (and the eventual field verticals) must not proceed. Never downgrade a mismatch to a warning.
3. Support **fault injection** for the test: a corrupted seed value (e.g. a mangled `shell_pid` or a
   flipped subtask status) must make verify abort. Expose the abort as a typed exception or a
   non-`"ok"` result the runner treats as terminal.
4. Wire the order: `backfill` → `verify` must run as a unit where `verify` failure prevents the caller
   from advancing (the reader/writer cutover happens in downstream WPs, so this WP's contract is: verify
   is callable, fail-closed, and returns an unambiguous go/no-go).

**Files**: `src/specify_cli/migration/backfill_runtime_state.py`.

**Validation checklist**:
- [ ] A clean backfill verifies `ok`.
- [ ] A fault-injected corrupt seed makes verify abort (no-go), asserted in the test.
- [ ] Verify compares both count and value (a value-only or count-only check is insufficient — test a
      count-match/value-mismatch case).
- [ ] Verify runs against the **un-stripped** frontmatter — assert that `strip_mutable_fields` has NOT
      run at verify time (a strip-then-verify ordering would produce a vacuous false green; test that
      inverting the order is caught).

**Edge cases**: an empty mission (no WPs) verifies `ok` trivially; a WP present in the snapshot but
absent from the legacy reader (or vice versa) is a count mismatch → abort.

### Subtask T013: Zero-reader verification for `history[]` / `progress`

**Purpose**: Prove `history[]` and `progress` have **zero** live readers before they are deleted (the
`history[]`/`add_history_entry` deletion is WP07/T028, the fallback deletion is WP10; this WP produces
the proof).

**Steps**:
1. Add a zero-reader verification (a test and/or an import/call-graph assertion under
   `tests/unit/migration/` or `tests/architectural/`) proving no live reader anywhere consumes
   `history[]` frontmatter or `progress` — not merely no *authority*-read. Reference the known legacy
   readers documented above (`workflow_cores.py:328-348`, and `_extract_done_evidence` at
   **`src/specify_cli/merge/done_bookkeeping.py:95`** — the `merge/` subtree, so the zero-reader grep
   targets `src/specify_cli/merge/done_bookkeeping.py`, not a top-level file) to confirm they read
   `review_status`/`review_feedback`/`reviewed_by` (which ARE zero-reader after strip+backfill) and
   that neither `history[]` nor `progress` has any remaining consumer.
2. Do **not** delete `add_history_entry`, the `history[]` field, or the fallbacks — those deletes are
   **WP07/T028** (`add_history_entry` + `__all__` + `test_no_dead_symbols` allowlist) and WP10
   (`workflow_cores`/`merge/done_bookkeeping` fallbacks). Your deliverable is the **verification** that
   makes those deletes safe.

**Files**: `tests/unit/migration/test_backfill_runtime_state.py` (zero-reader assertions) and/or a
targeted grep-based assertion helper in the backfill module.

**Validation checklist**:
- [ ] The zero-reader check passes for `history[]` and `progress` (no live reader).
- [ ] The check would **fail** if a reader were reintroduced (non-vacuous — assert against a stub).
- [ ] No deletion of `history[]`/`progress`/`add_history_entry`/the fallbacks happens in this WP.

**Edge cases**: a reader that reads `progress` only inside dead/unreachable code — decide whether that
counts (prefer: flag it, since "dead" must be proven, not assumed).

### Subtask T014: Migration idempotency + fail-closed tests

**Purpose**: The SC-006 acceptance surface — idempotency, parity, and the fail-closed abort.

**Steps**:
1. Create `tests/integration/test_migration_backfill.py` (register `integration` marker): on a fixture
   whose pre-state **carries evictable frontmatter+checkbox state**, run backfill #1 → assert N>0 seeds
   and the post-migration reduced snapshot equals the OLD reader's snapshot (count+value); run #2 →
   assert 0 new seeds (idempotent, NFR-002); inject a corrupt seed → assert verify **aborts before
   cutover** (fail-closed, SC-006).
2. Create `tests/unit/migration/test_backfill_runtime_state.py`: unit-level determinism (seed ids
   byte-identical across runs), clamp honesty (subtask `at == claimed`), the precondition assertion
   that no consumer reads subtask-completion time / relies on seed-ULID chronological order, and the
   `MUTABLE_FIELDS`/`STATIC_FIELDS` reclassification from T010.
3. Include a proof that `strip_mutable_fields` + backfill round-trips: strip a fixture, backfill,
   reduce, and assert parity with the pre-strip legacy read.

**Files**: `tests/integration/test_migration_backfill.py` (new),
`tests/unit/migration/test_backfill_runtime_state.py` (new).

**Validation checklist**:
- [ ] Run #1 seeds N>0, run #2 seeds 0.
- [ ] Corrupt-seed fault injection aborts verify before cutover.
- [ ] Determinism and clamp assertions pass.
- [ ] The precondition (no reader of completion-time / seed-ULID chronology) is asserted explicitly.

**Edge cases**: a fixture already fully backfilled (run #1 == 0) is a valid idempotency check; a fixture
with a never-claimed WP exercises the T011 clamp-anchor fallback.

## Branch Strategy

- **Planning base branch**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Final merge target**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Strategy**: `lane-per-wp`. Execution worktrees allocated per computed lane from `lanes.json`. WP03
  depends on WP01 and lands in the early band alongside WP02 (both gate the downstream verticals). The
  fail-closed verify this WP ships is the gate every field vertical's authority activation depends on
  (WP05–WP09); the fallback-delete it makes safe is handed to WP10.

## Definition of Done

- [ ] `MUTABLE_FIELDS` extended with `shell_pid_created_at`/`review_artifact_override_*`/
      `reviewer_shell_pid`/`history`; `history` moved out of `STATIC_FIELDS` **and into
      `MUTABLE_FIELDS`** so the corpus strip removes it (mirroring `progress`); `progress` retired
      explicitly (FR-010, T010).
- [ ] `backfill_runtime_state.py` seeds claim transitions + `InnerStateChanged` annotations with
      deterministic namespaced ULIDs, idempotently, clamping subtask `at` to `claimed` (FR-011, T011).
- [ ] `verify_backfill` is fail-closed: count+value parity vs the OLD reader; any mismatch or corrupt
      seed aborts before reader cutover (FR-011/SC-006, T012).
- [ ] Zero-reader verification proves `history[]`/`progress` have no live reader; no deletes performed
      here (FR-010, T013).
- [ ] Idempotency + fail-closed + determinism + clamp + precondition tests pass (SC-006/NFR-002, T014).
- [ ] Seeds resolve their write target from stored topology, never `Path.cwd()` (C-003).
- [ ] `pytest tests/integration/test_migration_backfill.py tests/unit/migration`, `ruff check
      src/specify_cli/migration/`, and `mypy src/specify_cli/migration/` are green.
- [ ] No changes outside `owned_files` (in particular: no deletes in `workflow_cores.py`,
      `src/specify_cli/merge/done_bookkeeping.py`, or `frontmatter.py`).

## Risks

- **ULID ordering at equal `at`.** A seed annotation that sorts *before* its transition would (absent
  the WP01 partition) clobber a slot; keep the seed id deterministic and ordered-after, and lean on the
  WP01 event-kind partition. Test the equal-`at` case.
- **Fail-closed abort weakened to a warning.** The single most dangerous regression — a mismatch that
  logs-and-continues reopens the clobber window. The abort must be terminal; the fault-injection test
  guards it.
- **Clamp dishonesty.** "No data loss" holds only under count+value parity with the completion-time /
  seed-chronology precondition asserted. If a consumer later reads completion time, the contract breaks
  — assert the precondition now.
- **Premature deletion.** Deleting the legacy fallbacks or `history[]`/`add_history_entry` here would
  clobber un-migrated on-disk WPs. Those deletes are WP07/T028 (`history[]`/`add_history_entry`) and
  WP10 (fallbacks), gated on this backfill — do not pull them forward.

## Reviewer guidance

- Confirm the strict order is respected: this WP ships backfill + verify + field reclassification only;
  no reader/writer cutover, no fallback deletes.
- Confirm seed ids are deterministic (byte-identical across runs) and namespaced (`mission_id+wp_id+
  field`), and that the annotation seed sorts after its transition at equal `at`.
- Confirm verify compares **both** count and value, and that a count-match/value-mismatch case aborts.
- Confirm the fault-injection test actually corrupts a seed and observes a terminal abort (non-vacuous).
- Confirm the clamp is honest (subtask `at == claimed`) and the no-completion-time-reader precondition
  is asserted, not assumed.
- Confirm nothing was deleted that belongs to WP07/T028 (`add_history_entry`, `history[]`) or WP10
  (the `workflow_cores`/`merge/done_bookkeeping` fallbacks).
- Confirm no `Path.cwd()` in the new module.

## Activity Log

- 2026-07-19T10:49:54Z – claude:opus:python-pedro:implementer – shell_pid=2440108 – Assigned agent via action command
- 2026-07-19T11:11:58Z – claude:opus:python-pedro:implementer – shell_pid=2440108 – Ready: MUTABLE_FIELDS+history, deterministic-ULID backfill, fail-closed pre-strip verify; idempotency+fault-injection green
- 2026-07-19T11:13:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=2517029 – Started review via action command
- 2026-07-19T11:18:21Z – user – shell_pid=2517029 – Review passed: T010 history moved STATIC->MUTABLE (+RETIRED_FIELDS marker, new evicted keys enumerated), strip removes history/progress (tested). T011 deterministic namespaced ULIDs (byte-identical, idempotent run#2=0), subtask at clamped to claimed, canonicalize_feature_dir never Path.cwd; reuses sanctioned wp_state.annotate() seam with caller-minted event_id (annotate docstring parameterizes event_id; emit_inner_state_changed is just annotate+random-ULID) -- ownership-respecting, not a fork; seeds proven reducible by real materialize_snapshot. T012 fail-closed verify on UN-stripped frontmatter, non-vacuous ordering guard raises MigrationOrderingError on strip-then-verify (tested), count-match/value-mismatch aborts (T001 flip), corrupt-seed + unreadable-log abort. T013 zero-reader proof non-vacuous vs stub; history writer seams (frontmatter.py/wp_metadata.py) excluded belong to WP07/T028; no out-of-scope deletes. Scope clean: only owned_files touched, sole deletion is STATIC_FIELDS history line; no edits to workflow_cores/merge.done_bookkeeping/frontmatter.py. 65 pytest passed, ruff clean, WP03 files mypy-clean (3 pre-existing mypy errors in untouched rewrite_shims.py/normalize_mission_lifecycle.py). Note: backfill engine not yet CLI/runner-wired, but those files are outside owned_files -- downstream WP concern, not a defect.
