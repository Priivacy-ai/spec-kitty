---
work_package_id: WP01
title: Event foundation + reducer fold + emit API
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-opus-4-8
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
create_intent:
- tests/architectural/test_innerstatechanged_invariants.py
- tests/unit/status/test_innerstatechanged_reducer_fold.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/store.py
- src/specify_cli/status/reducer.py
- src/specify_cli/status/wp_state.py
- src/specify_cli/status/emit.py
- tests/unit/status/**
- tests/architectural/test_innerstatechanged_invariants.py
role: implementer
tags: []
shell_pid: "2374828"
shell_pid_created_at: "1784456746.12"
---

# WP01 — Event foundation + reducer fold + emit API

## ⚡ Do This First: Load Agent Profile

Before reading any further, run `/ad-hoc-profile-load python-pedro` and adopt the profile in full:
its identity (idiomatic, type-safe Python 3.12+ implementer), its directives (TDD red→green→refactor,
type hints on every public API, run the full `pytest` / `ruff` / `mypy` gate before handoff), its
tactics (pydantic/dataclass validation, `pathlib`, protocol patterns), and — critically — its
**boundaries**: you do **not** make architectural decisions here. The reducer contract, the event-kind
partition, and the snapshot slot set are already ratified in the design of record below. Implement them
faithfully; if a genuine structural ambiguity surfaces, stop and escalate rather than inventing a shape.

## Objective

Lay the event-sourcing foundation the entire mission stands on: introduce the single generic off-axis
`InnerStateChanged` event carrying a **typed** `WPInnerStateDelta`, make it visible to the reducer
through a distinct annotation read path, and teach the reducer to **branch on event kind** so lane
transitions preserve the runtime slots they do not write while annotations apply a per-field-merged
delta in a dedicated post-transition pass. The reduced snapshot gains the typed runtime slots every
downstream field vertical reads (`shell_pid`, `shell_pid_created_at`, `subtasks`, `notes`,
`tracker_refs`, `agent`, `assignee`, `review`), the `planned→claimed` transition folds its
`policy_metadata` sidecar into those slots, and `emit.py` grows the `emit_inner_state_changed` API plus
a snapshot-sourced `_infer_subtasks_complete`. This WP ships no writer cutover — it is the P1
foundation that WP02–WP10 depend on, proven in isolation by unit fold tests and an architectural
invariant test.

## Context

**Design of record**: ADR `docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md`.
This WP realises **IC-01** (off-axis event class + reducer fold foundation) from `plan.md`.

**Requirements owned here**: FR-001 (the event, discriminator, distinct read path, arch test),
FR-002 (reducer branch-on-kind, slot preservation, event-kind partition, snapshot slots), the fold
half of FR-004 (the `planned→claimed` `policy_metadata`→snapshot extraction), the snapshot-source half
of FR-003 (`_infer_subtasks_complete` re-source), C-002 (typed delta, never a free dict), C-004 (FSM
matrix untouched — `InnerStateChanged` bypasses `validate_transition` via a sanctioned non-transition
path, it does NOT add self-edges), and NFR-005 (O(events), no extra re-reduction pass).

**Design-of-record facts you must honour** (see `contracts/innerstatechanged-event.md` and
`data-model.md`):

- **The reducer replace-dict hazard.** Today `reducer.py::_wp_state_from_event` (`reducer.py:48-65`)
  rebuilds the per-WP dict on every event, carrying forward **only** `force_count`
  (`reducer.py:57,64`). If you fold runtime slots naively, the very next lane transition erases
  `shell_pid`/`subtasks`/`notes`/`tracker_refs`. A transition MUST **preserve** untouched runtime slots.
- **Event-kind partition, not `at`-interleave.** Fold **all transitions first**, then **all
  annotations** in a dedicated second pass. A same-`at` transition must never clobber an annotation
  slot; a backfill seed annotation must fold *after* the transition it annotates at equal `at`.
- **Snapshot slot set** is `{shell_pid, shell_pid_created_at, subtasks, notes, tracker_refs, agent,
  assignee, review}` — this includes `agent`/`assignee` and a `review` slot (the authority table
  asserted these with no carrier; you are the carrier).
- **Claim `policy_metadata` fold.** The `planned→claimed` transition is the **only** transition that
  writes a runtime slot: it extracts `shell_pid`/`shell_pid_created_at`/`agent` from its existing
  `policy_metadata` sidecar (`models.py:258`) into the snapshot slots. Every other runtime slot is
  written by an `InnerStateChanged`.
- **Discriminator must not collide with the `event_type` skip.** `store.is_non_lane_event`
  (`store.py:459-486`) today skips **any** dict where `"event_type" in obj` (`store.py:486`) — a
  presence check, not a value allowlist. Your annotation discriminator is `kind == "annotation"`
  (`contracts/innerstatechanged-event.md`); reconcile it so annotations are **surfaced** to `reduce()`,
  not skipped, and never routed through `StatusEvent.from_dict` (which hard-requires `from_lane`/
  `to_lane` at `models.py:302-303`).

Point of truth for wire shape and fold order: `contracts/innerstatechanged-event.md`. Typed payload and
merge rules: `data-model.md` §`WPInnerStateDelta`.

### Subtask T001: `InnerStateChanged` + typed `WPInnerStateDelta` models

**Purpose**: Define the new off-axis event and its typed partial payload in `status/models.py`, as
frozen dataclasses that sit beside `StatusEvent` (`models.py:231-261`) but carry **no**
`from_lane`/`to_lane` and can never traverse the FSM.

**Steps**:
1. In `src/specify_cli/status/models.py`, add `@dataclass(frozen=True) class WPInnerStateDelta` with
   typed **optional** fields (C-002 — never `dict[str, Any]`): `shell_pid: int | None = None`,
   `shell_pid_created_at: str | None = None`, `subtasks: Mapping[str, str] | None = None`
   (subtask-id → `Status`; reuse the existing lane/status enum vocabulary rather than a new string
   type), `note: str | None = None`, `tracker_refs: list[str] | None = None`,
   `tracker_refs_replace: list[str] | None = None`, `agent: str | None = None`,
   `assignee: str | None = None`, `review: ReviewOverride | None = None`. **WP01 defines
   `tracker_refs_replace` here** — it is the delta-level *replace* channel (distinct from the additive
   `tracker_refs` union) that WP08's `--replace` needs so a replace does not resurrect stale refs; the
   reduced snapshot union slot stays named `tracker_refs` (the replace field is a delta input only, never
   a separate snapshot slot). Its reducer semantics are pinned in T003.
2. Define a small frozen `ReviewOverride` with **exactly** these fields — `at: str`, `actor: str`,
   `wp_id: str`, `reason: str` — plus a `complete` predicate defined as **all four fields non-empty**
   (`bool(at and actor and wp_id and reason)`). Do **not** reuse the review-result shape near
   `wp_state.py:612-629`, and do not invent `review_artifact_override_*` fields — WP03/WP09 reference the
   `{at, actor, wp_id, reason}` fields and the `complete` predicate **verbatim**, so this shape is
   pinned, not a suggestion. WP09 consumes this slot, so define it, do not stub it.
3. Add `@dataclass(frozen=True) class InnerStateChanged` with fields matching the contract:
   `event_id: str`, `kind: str = "annotation"`, `wp_id: str`, `at: str`, `actor: str`,
   `delta: WPInnerStateDelta`. Follow `StatusEvent`'s frozen/immutable conventions (`models.py:231`).
4. Give it a `to_dict()` mirroring `StatusEvent.to_dict` (`models.py:263-283`) but emitting `kind`,
   `wp_id`, `at`, `actor`, and a nested `delta` with **only present** fields (absent fields omitted so
   the reducer's "absent leaves slot untouched" rule is unambiguous on the wire).
5. Add a **distinct** decoder `InnerStateChanged.from_dict(obj)` that does **not** reuse
   `StatusEvent.from_dict` (which subscripts `data["from_lane"]`/`data["to_lane"]` at
   `models.py:302-303` and would `KeyError`). Validate `event_id` against `ULID_PATTERN`
   (`models.py:93`, currently defined-but-unused — put it to work here), require `kind ==
   "annotation"`, and build the typed `WPInnerStateDelta` from `obj["delta"]`, coercing each present
   field to its declared type.

**Files**: `src/specify_cli/status/models.py`.

**Validation checklist**:
- [ ] `WPInnerStateDelta` has zero `Any`-typed fields (`mypy --strict` on the module is clean).
- [ ] `WPInnerStateDelta` carries both `tracker_refs` (union) and `tracker_refs_replace` (replace) as
      distinct optional fields.
- [ ] `ReviewOverride` has **exactly** `{at, actor, wp_id, reason}` and a `complete` predicate that is
      `True` only when all four are non-empty.
- [ ] `InnerStateChanged` has no `from_lane`/`to_lane` attribute and no `force`/`force_count`.
- [ ] Round-trip `InnerStateChanged.from_dict(e.to_dict()) == e` for a delta touching each field.
- [ ] A `to_dict()` of a delta with only `note` set emits **just** `{"note": ...}` under `delta`.

**Edge cases**: an empty delta (all fields `None`) is a legal-but-inert event — decide and document
(prefer: constructable, folds to a no-op, but `emit_inner_state_changed` in T005 refuses to emit one);
`event_id` failing `ULID_PATTERN` raises a typed error, never silently passes.

### Subtask T002: Wire discriminator + store read path

**Purpose**: Make annotations structurally visible to `reduce()` without breaking the existing
transition read path — reconcile the `is_non_lane_event` presence-skip and route annotations to the
new decoder.

**Steps**:
1. In `src/specify_cli/status/store.py`, teach `is_non_lane_event` (`store.py:459-486`) that a dict
   with `kind == "annotation"` is **not** a skip-and-drop event. Today the final line
   (`store.py:486`) returns `"event_type" in obj`; annotations carry `kind`, not `event_type`, so they
   already avoid that specific skip — but you must add an explicit, tested branch so a future
   `event_type` addition to the annotation envelope can never silently re-skip it. Keep the
   retrospective skips (`store.py:461-469`) intact.
2. In `read_events_from_text` (`store.py:489-529`), where the loop currently calls
   `StatusEvent.from_dict(obj)` at `store.py:525` (guarded by `if is_non_lane_event(obj): continue` at
   `store.py:515`), add a partition: dicts with `kind == "annotation"` decode via
   `InnerStateChanged.from_dict(obj)` and flow into a **separate** annotation list (or a tagged
   union), while lane events continue through `StatusEvent.from_dict`. Preserve the existing
   `StoreError` wrapping with the 1-based line number (`store.py:526-527`).
3. Expose the annotations to `reduce()` — extend `read_events` (`store.py:532-549`) / its return type
   so the reducer receives both transitions and annotations (a small typed container, e.g.
   `EventStream(transitions=[...], annotations=[...])`, or a single ordered list the reducer
   partitions). Do not change the on-disk file; this is a read-shape change only.

**Files**: `src/specify_cli/status/store.py` (and the return-type touch in `models.py` if you define a
container there).

**Validation checklist**:
- [ ] A jsonl fixture mixing `transition` and `annotation` lines reads without `StoreError`.
- [ ] `is_non_lane_event` returns the correct classification for: a transition, an annotation, a
      retrospective event, and a hypothetical `event_type`-bearing annotation (still surfaced).
- [ ] An annotation line is **never** passed to `StatusEvent.from_dict` (assert via a spy/patch that it
      raises if it were).

**Edge cases**: a malformed annotation (missing `delta`) raises `StoreError` with its line number, not
a bare `KeyError`; an unknown `kind` value is treated as a hard error, not silently skipped (fail
loud — a silent skip would lose runtime state).

### Subtask T003: Reducer branch-on-kind + preserve slots + partition fold + snapshot slots

**Purpose**: The heart of the WP. Make the reducer branch on event kind, preserve untouched runtime
slots across transitions, fold annotations in a dedicated post-transition pass with per-field merge,
and add the typed snapshot slots.

**Steps**:
1. In `src/specify_cli/status/reducer.py`, extend the per-WP snapshot dict built by
   `_wp_state_from_event` (`reducer.py:48-65`). Today it returns only `lane`/`actor`/
   `last_transition_at`/`last_event_id`/`force_count` (`reducer.py:59-65`) and carries forward only
   `force_count` (`reducer.py:57`). Change it to **carry forward all runtime slots** from `previous`
   (`shell_pid`, `shell_pid_created_at`, `subtasks`, `notes`, `tracker_refs`, `agent`, `assignee`,
   `review`) — a transition updates lane/actor/… and leaves those untouched (per-field independence,
   FR-002).
2. Add the **claim exception**: when the event is the `planned→claimed` transition, extract
   `shell_pid`/`shell_pid_created_at`/`agent` from `event.policy_metadata` (`models.py:258`) into the
   snapshot slots. This is the **only** transition that writes a runtime slot (FR-004 claim path;
   `contracts/innerstatechanged-event.md` step 2). Read defensively — `policy_metadata` may be `None`.
3. Restructure `reduce()` (`reducer.py:118-187`) into an **event-kind partition**: first fold all
   transitions in the existing `(at, event_id)` order (`reducer.py:153`, dedup at `reducer.py:144-150`
   preserved), producing lane + carried runtime slots; **then** run a second pass folding all
   annotations, applying `WPInnerStateDelta` per-field merge: **replace** for `shell_pid`/
   `shell_pid_created_at`/`agent`/`assignee`/`review`, **per-subtask replace** for `subtasks`,
   **append** for `note` → the `notes` list, and for tracker refs a **two-channel** rule into the single
   `tracker_refs` snapshot slot: `tracker_refs` (additive) **unions** into the slot, while
   `tracker_refs_replace` (present) **wholesale-replaces** the slot with that exact list (dedup-preserving
   order) and takes precedence when both are present in one delta. The replace channel is what lets WP08's
   `--replace` drop stale refs — a union alone would resurrect them. Only present delta fields are
   applied; absent fields leave the slot untouched. Annotations **never** increment `force_count`.
4. Ensure the annotation pass is **O(annotations)** with no second `reduce()` over transitions
   (NFR-005) — a single linear pass keyed by `wp_id`. Do not re-scan the transition list per field.

**Files**: `src/specify_cli/status/reducer.py`.

**Validation checklist** (unit tests land in T006, but design them as you go):
- [ ] A transition following a `subtasks` annotation preserves the `subtasks` slot (replace-dict hazard
      closed).
- [ ] `planned→claimed` with `policy_metadata={"shell_pid":123,...}` sets the `shell_pid` slot.
- [ ] Two `note` annotations append in order → `notes == [n1, n2]`.
- [ ] `tracker_refs` union dedups; per-subtask `subtasks` replace merges by id.
- [ ] `tracker_refs_replace` wholesale-replaces the `tracker_refs` slot (stale refs dropped, not
      resurrected) and wins over a same-delta `tracker_refs` union.
- [ ] `force_count` is unchanged by any annotation.

**Edge cases**: same-`at` transition + seed annotation → annotation wins its slot (partition order, not
timestamp); a `planned→claimed` with `policy_metadata=None` leaves runtime slots empty (no crash); an
annotation for a `wp_id` with no prior transition folds onto an empty base snapshot (define whether
that is legal — prefer: legal, materialises a runtime-only WP entry).

### Subtask T004: Sanctioned non-transition `annotate()` path (no FSM matrix change)

**Purpose**: Provide the code seam that constructs and validates an `InnerStateChanged` without
touching `validate_transition` or the 9-lane / 27-pair matrix (C-004).

**Steps**:
1. In `src/specify_cli/status/wp_state.py`, add a small sanctioned non-transition helper (e.g.
   `annotate(wp_id, delta, *, actor, at, event_id) -> InnerStateChanged`). There is **no** existing
   `annotate()` path today (the module is a pure state machine; closest analogue is
   `UninitializedState.allowed_targets()` returning `frozenset()` at `wp_state.py:283-284`, which
   deliberately adds zero edges). Model your helper on that "adds zero edges" discipline.
2. The helper MUST NOT call `validate_transition` (`transitions.py:68`) and MUST NOT add lane
   self-edges to the matrix. It only constructs the typed event; validation is delta-shape validation,
   not FSM validation.
3. Keep `_check_review_result` and its consistency checks (`wp_state.py:612-659`) untouched — WP02/WP15
   depend on that structured-review-object contract (`wp_state.py:624`).

**Files**: `src/specify_cli/status/wp_state.py`.

**Validation checklist**:
- [ ] `annotate()` never references `validate_transition` (grep/import assertion in T006 arch test).
- [ ] The FSM matrix (`transitions.py`) is byte-unchanged by this WP.
- [ ] `annotate()` returns a fully-typed `InnerStateChanged`; an empty delta is refused here.

**Edge cases**: an `at` in the future or a non-UTC `at` — accept but normalise consistently with
existing event timestamps; a `wp_id` not matching `_WP_ID_PATTERN` (`store.py:43`) is refused.

### Subtask T005: `emit_inner_state_changed` API + claim fold + `_infer_subtasks_complete` re-source

**Purpose**: Ship the public emit API downstream WPs call, and re-source done-inference to the snapshot.

**Steps**:
1. In `src/specify_cli/status/emit.py`, add `emit_inner_state_changed(...)` beside the existing emit
   functions. Mint a real ULID via the module's existing `_generate_ulid()` (`emit.py:113`, used at
   `emit.py:179,559,605,734`), build the `InnerStateChanged` via the T004 `annotate()` path, and
   persist it through the store append seam (`store.append_events_atomic_verified` — the
   durability-verified path; see `store.py:382-395`). **Resolve the write target via
   `canonicalize_feature_dir(feature_dir)`** (`emit.py:522,676,687`) — never `Path.cwd()` (FR-012 /
   C-003 / #2647). There is no `Path.cwd()` in `status/` today; keep it that way.
2. Re-source `_infer_subtasks_complete` (`emit.py:279-302`), **gated behind the dual-write flag**. Today
   it reads `tasks.md` **text** (`emit.py:298`) and delegates to `count_wp_section_subtask_rows`
   (`emit.py:299`). Add the snapshot re-source path — materialise the snapshot for the WP and count
   done-vs-total from the reduced `subtasks` slot — **but guard it behind
   `_phase1_dual_write_enabled(feature_dir)`** (the flag already exists at `emit.py:310`; import the
   exact symbol, do not re-derive it). When the flag is **off**, keep reading the legacy `tasks.md` text;
   only when it is **on** read the snapshot slot. This gate is mandatory because WP01 lands **before**
   WP03 flips/verifies the flag: an ungated cut would read an empty snapshot and return `False` for
   **every** WP the moment WP01 merges, silently breaking the done-inference gate before any writer has
   populated the slot. Keep it **fail-closed** on both paths: an absent/empty snapshot (flag on) or an
   absent file (flag off) returns `False` (do not fail open), matching the current absent-file behaviour
   (`emit.py:296-297`). Preserve the call-site guards at `emit.py:541-545` and `emit.py:699-703` (only
   fires on `in_progress → for_review`).
3. Keep the claim `policy_metadata` fold *reducer-side* (T003) — do not add a second read path here.
4. **WP01 owns the two shared symbols every reader/writer WP imports.** (a) The dual-write flag
   `status/emit.py::_phase1_dual_write_enabled(feature_dir)` — it **already exists at `emit.py:310`**;
   WP01 owns its *semantics* (the canonical gate for phase-1 snapshot reads/writes) and every downstream
   WP imports this exact symbol rather than re-deriving a local flag. WP01 does **NOT** delete the flag:
   teardown is per-owning-lane (each lane removes its own gate once cut over), and **WP10 only verifies**
   the flag is gone — it does not own removal here. (b) The shared claim builder
   `status/emit.py::build_claim_policy_metadata(shell_pid, shell_pid_created_at, agent) -> dict`, which
   returns the `planned→claimed` `policy_metadata` sidecar with exactly the pinned keys `shell_pid`,
   `shell_pid_created_at`, `agent` — the same keys T003's reducer fold extracts. Define it here so the
   claim writer WP and the reducer agree on one shape; downstream WPs import this exact symbol.

**Files**: `src/specify_cli/status/emit.py`.

**Validation checklist**:
- [ ] `emit_inner_state_changed` writes exactly one annotation line, readable back by T002's path.
- [ ] An emit run from a cwd different from the mission root lands at the canonicalised feature dir
      (mini SC-008 smoke; the full cross-package test is WP08).
- [ ] With `_phase1_dual_write_enabled` **on**, `_infer_subtasks_complete` returns `True` only when the
      snapshot `subtasks` slot shows all done; returns `False` on an empty snapshot (fail-closed).
- [ ] With `_phase1_dual_write_enabled` **off**, `_infer_subtasks_complete` still reads legacy `tasks.md`
      (the pre-WP03 default — an ungated snapshot cut would return `False` for every WP).

**Edge cases**: emitting an empty delta is refused; a WP with zero subtasks in the snapshot →
`_infer_subtasks_complete` returns `True` (matches the `total == 0` branch at `emit.py:300-301`).

### Subtask T006: Unit fold tests + architectural invariant test

**Purpose**: Prove the fold contract and pin the "annotation is never a lane transition" invariant.

**Steps**:
1. Create `tests/unit/status/test_innerstatechanged_reducer_fold.py` covering: slot preservation
   across a transition; the `planned→claimed` `policy_metadata`→slot extraction; per-field merge
   (replace / per-subtask replace / append / union); `force_count` never bumped by an annotation;
   same-`at` partition ordering (annotation folds after transition); O(events) — assert **structurally**
   that the annotation fold does **not re-scan the transition list** (no per-field re-scan): it is not
   enough to assert `reduce()` runs once. Drive a stream with N transitions and M annotations and assert
   the transition list is visited exactly once total (e.g. instrument/spy the transition iterable and
   assert its access count is independent of M — folding annotations must not re-walk transitions
   per-field or per-annotation), so an accidental O(transitions × annotation-fields) fold fails the test.
2. Create `tests/architectural/test_innerstatechanged_invariants.py` asserting: an `InnerStateChanged`
   can **never** be reduced as a lane transition (feed one through `reduce()`, assert `lane` is
   untouched and `force_count` unchanged); `is_non_lane_event` surfaces it; `StatusEvent.from_dict` is
   never invoked on an annotation dict; and the `annotate()` path does not import/reference
   `validate_transition` (import/call-graph assertion).

**Files**: `tests/unit/status/test_innerstatechanged_reducer_fold.py` (new),
`tests/architectural/test_innerstatechanged_invariants.py` (new). Register the `architectural`/`unit`
markers per `pytest.ini`.

**Validation checklist**:
- [ ] Both new test files pass under `pytest`.
- [ ] The arch test fails if a naive reducer folds an annotation as a transition (mutation test it once
      locally to confirm it is not vacuously green).

**Edge cases**: a fold over an empty event stream yields an empty snapshot (no crash); an annotation-only
stream (no transitions) materialises a runtime-only WP entry per the T003 decision.

## Branch Strategy

- **Planning base branch**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Final merge target**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Strategy**: `lane-per-wp`. Execution worktrees are allocated per computed lane from `lanes.json`
  after `finalize-tasks` runs. As the P1 foundation with no dependencies, WP01 is first on the critical
  path — expect lane A. Land it before WP02/WP03 rebase onto `status/` so the reducer/store shapes are
  stable.

## Definition of Done

- [ ] `InnerStateChanged` + `WPInnerStateDelta` (+ `ReviewOverride`) are typed frozen dataclasses with
      no `Any` fields (C-002) and round-trip cleanly (T001).
- [ ] `WPInnerStateDelta` defines the `tracker_refs_replace: list[str] | None` delta field alongside the
      additive `tracker_refs` (WP08's `--replace` channel; T001).
- [ ] `ReviewOverride` has exactly the pinned fields `{at, actor, wp_id, reason}` and a `complete`
      predicate (all four non-empty) — no `review_artifact_override_*` shape (T001).
- [ ] Annotations are surfaced to `reduce()` via a distinct read path and never routed through
      `StatusEvent.from_dict` (FR-001, T002).
- [ ] The reducer branches on kind, preserves untouched runtime slots across transitions, folds
      annotations in an event-kind-partition post-pass with correct per-field merge, and never bumps
      `force_count` on an annotation (FR-002, T003).
- [ ] The tracker-refs fold is two-channel: `tracker_refs` unions into the slot, `tracker_refs_replace`
      wholesale-replaces it (stale refs dropped) and wins when both are present (T003).
- [ ] `planned→claimed` extracts `shell_pid`/`shell_pid_created_at`/`agent` from `policy_metadata` into
      the snapshot slots (FR-004 fold half, T003).
- [ ] The snapshot exposes all eight typed runtime slots (`data-model.md`).
- [ ] `annotate()` bypasses `validate_transition`; the FSM matrix is byte-unchanged (C-004, T004).
- [ ] `emit_inner_state_changed` persists via the verified store seam and resolves its target from
      stored topology, never `Path.cwd()` (FR-012, T005).
- [ ] WP01 owns the shared symbols `_phase1_dual_write_enabled(feature_dir)` (already at `emit.py:310`,
      not deleted here — WP10 only verifies) and `build_claim_policy_metadata(shell_pid,
      shell_pid_created_at, agent) -> dict` (pinned keys); downstream WPs import these exact symbols
      (T005).
- [ ] `_infer_subtasks_complete` reads the snapshot `subtasks` slot **only when
      `_phase1_dual_write_enabled` is on**, falls back to legacy `tasks.md` when off (WP01 lands before
      WP03 verify), and is fail-closed on both paths (FR-003 source half, T005).
- [ ] The fold is O(events) with no extra re-reduction pass, and the annotation fold does **not re-scan
      the transition list** (no per-field/per-annotation re-walk), asserted structurally (NFR-005, T006).
- [ ] The architectural invariant test passes and is non-vacuous (T006).
- [ ] `pytest tests/unit/status tests/architectural/test_innerstatechanged_invariants.py`, `ruff check
      src/specify_cli/status/`, and `mypy src/specify_cli/status/` are all green.
- [ ] No changes outside `owned_files`.

## Risks

- **The reducer replace-dict hazard** (highest). `_wp_state_from_event` rebuilds the per-WP dict; if you
  forget to carry forward a runtime slot, a later transition silently erases it and downstream WPs read
  stale/empty state. Mitigate with the slot-preservation unit test *before* the writer WPs land.
- **Discriminator collision.** The `event_type`-presence skip (`store.py:486`) is a blunt instrument;
  an annotation that ever grows an `event_type` key would be silently dropped. Pin the classification
  with an explicit tested branch.
- **Ordering partition.** A timestamp-interleave fold (instead of the kind partition) clobbers slots
  non-deterministically at equal `at`. The partition is the design of record — do not "optimise" it
  into a single sorted pass.
- **Claim-path `policy_metadata` may be `None`.** Read defensively; a missing sidecar is not an error.

## Reviewer guidance

- Confirm the reducer **partition** (all transitions, then all annotations) is real, not an `at`-sorted
  single pass — check the equal-`at` seed-annotation test actually exercises the ordering.
- Confirm a transition after an annotation preserves every runtime slot, not just the ones the test
  happened to set — look for a slot the test forgot.
- Confirm `annotate()`/`emit_inner_state_changed` have zero references to `validate_transition` and zero
  `Path.cwd()` — grep both.
- Confirm `WPInnerStateDelta` is genuinely typed (no `dict[str, Any]` leak through `review`/`subtasks`).
- Confirm the NFR-005 assertion is structural (single pass), not a wall-clock threshold.
- Confirm the arch test is non-vacuous: it should fail against a deliberately-broken reducer.

## Activity Log

- 2026-07-19T09:35:33Z – claude:opus:python-pedro:implementer – shell_pid=2298344 – Assigned agent via action command
- 2026-07-19T09:35:57Z – claude:opus:python-pedro:implementer – shell_pid=2299412 – Assigned agent via action command
- 2026-07-19T10:24:09Z – claude:opus:python-pedro:implementer – shell_pid=2299412 – Ready: event class + reducer fold + emit API + flag-gated infer; unit+arch green (1117 passed/4 skipped), diff-lint ruff 0
- 2026-07-19T10:25:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=2374828 – Started review via action command
- 2026-07-19T10:46:59Z – user – shell_pid=2374828 – Review passed: typed InnerStateChanged/WPInnerStateDelta/ReviewOverride foundation; event-kind-partition reducer fold with per-field slot preservation + claim policy_metadata fold; annotations reach reduce() live via read_event_stream in materialize_snapshot (production path); annotate() FSM-free and transitions.py byte-unchanged (C-004); pinned shared symbols intact; flag-gated _infer_subtasks_complete. Suite 1117 passed/4 skipped, ruff clean, zero new mypy errors, scope within owned_files.
