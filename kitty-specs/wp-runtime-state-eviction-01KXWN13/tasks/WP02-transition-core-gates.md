---
work_package_id: WP02
title: 'Transition-core gates: force-fix + subtask gate re-source'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-015
tracker_refs: []
planning_base_branch: mission-prep/2684-wp-runtime-state-eviction
merge_target_branch: mission-prep/2684-wp-runtime-state-eviction
branch_strategy: Planning artifacts for this mission were generated on mission-prep/2684-wp-runtime-state-eviction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission-prep/2684-wp-runtime-state-eviction unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-opus-4-8
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/regression/test_2684_force_provenance.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py
- tests/regression/test_2684_force_provenance.py
role: implementer
tags: []
shell_pid: "2548429"
shell_pid_created_at: "1784460091.24"
---

# WP02 — Transition-core gates: force-fix + subtask gate re-source

## ⚡ Do This First: Load Agent Profile

Before reading further, run `/ad-hoc-profile-load python-pedro` and adopt the profile: its identity
(type-safe Python 3.12+ implementer), its directives (TDD red→green→refactor, type hints on public
APIs, full `pytest`/`ruff`/`mypy` gate before handoff), its tactics, and its **boundaries** — you do
**not** redesign the FSM or the force-provenance policy here. The five exempt edges and the
"ask-the-FSM" mechanism are ratified in the design of record. Implement them faithfully; the moment you
feel tempted to hard-code an edge list, stop — that is the exact anti-pattern this WP exists to remove.

## Objective

Fix the false-force provenance bug and re-source the subtask gate, both of which live in
`tasks_transition_core.py`. First: stop `build_transition_plan` from auto-stamping `force=True` on the
**three plan-reachable** evidence-gated review-rejection backward edges (`in_progress→planned`,
`approved→in_progress`, `approved→planned`) — decided by **asking the FSM** whether the edge is legal
force-free given the supplied evidence, never by a frozen edge list (so it cannot rot if the matrix
changes). To carry review evidence in, `build_transition_plan` gains an **optional `review_result`
param** (default `None`); WP02 only threads the evidence it already has at the plan layer (`reason`/
`review_feedback_pointer`, `arb_review_ref`) into the FSM query for those three edges. The two
`in_review→*` edges need a **structured `review_result`** that is **not available at the plan layer
today** (the signature carries only the `review_feedback_pointer`/`arb_review_ref` scalars, and the
caller that could construct it — `tasks_move_task.py:1302` — is **WP06-owned**), so those two edges and
the construction/threading of `review_result` are **WP06's scope**, not WP02's. Second: re-source
`_guard_subtasks` to read subtask completion from the reduced snapshot (WP01's `subtasks` slot) instead
of `tasks.md` bytes. Land this early — right after WP01 — so every writer WP rebases onto corrected
force/gate logic. The WP is proven by a persisted-layer force-provenance regression driven through the
**real** move-task path over the three edges (plus a genuine-force positive control), plus re-pointed
existing plan-level force tests.

## Context

**Design of record**: ADR `docs/adr/3.x/2026-07-19-1-...innerstatechanged.md`. This WP realises
**IC-02** (force-provenance fix, LAND FIRST) and the `_guard_subtasks` half of **IC-04b** from
`plan.md`. Contract of record: `contracts/emit-force.md`.

**Requirements owned here**: FR-015 (ask-the-FSM force suppression; edge-specific evidence; re-point
existing tests; persisted assertion) — **scoped to the three plan-reachable edges**
(`in_progress→planned`, `approved→in_progress`, `approved→planned`) — and FR-003's gate half
(`_guard_subtasks` re-source to the reduced snapshot). Success criterion **SC-007** is **split by
layer**: WP02's persisted-force regression covers the **three** plan-reachable edges + a genuine-force
positive control via the real move-task entry point; **WP06 extends SC-007 to all five** once it
constructs and threads the structured `review_result` for the two `in_review→*` edges. **NFR-003** (0
false-force stamps) holds across the split.

**Explicitly moved to WP06** (do not implement here): the two `in_review→*` edges
(`in_review→planned`, `in_review→in_progress`) and the construction/threading of the structured
`review_result` object (reviewer + verdict + reference). WP02 only *adds the optional `review_result`
param* to `build_transition_plan`'s signature so WP06 has the seam to thread into; WP02 leaves it
defaulting to `None` and never populates it, because the caller `tasks_move_task.py:1302` that would
build it is WP06-owned.

**Design-of-record facts you must honour**:

- **Ask the FSM, not a frozen edge list.** The mechanism is: on a backward edge without explicit
  `--force`, query `validate_transition(old, target, ctx_with_evidence)` (force-free) and only promote
  `emit_force` when the FSM genuinely rejects it. The five-edge table in `contracts/emit-force.md` is
  **confirmatory/illustrative — NOT the implementation surface**; encoding it literally would rot when
  the matrix changes (FR-015, close-by-construction).
- **Evidence is edge-specific and not interchangeable.** `reason` for `in_progress→planned`;
  `review_ref`/`arb_review_ref` for `approved→*` — **these two evidence types are available at the plan
  layer today, so WP02 wires them for its three edges.** A **structured `review_result` object**
  (reviewer + verdict + reference) is required for the two `in_review→*` edges (a scalar reason is
  rejected at `wp_state.py:624`); that object is **not available at the plan layer today** and is
  **WP06's** responsibility to construct/thread — WP02 does not supply it. The FSM already enforces this
  via `_check_review_result` (`wp_state.py:612-629`) — you supply the evidence into the context, the FSM
  decides legality.
- **Persisted-force assertion via the real move-task.** SC-007 is the **persisted** `StatusEvent.force`
  read off `status.events.jsonl` after driving the real move-task entry point — **not** the plan
  object. Add the command-layer regression and re-point (delete-the-assertion-not-the-test) the
  enumerated existing plan-level tests.
- **Re-source the gate, do not delete it.** `_guard_subtasks` still refuses genuinely-incomplete WPs;
  it just reads the reduced snapshot instead of `tasks.md` bytes. The refusal branch stays.

Point to `contracts/emit-force.md` for the exact FSM-query shape and the SC-007 assertion surface.

### Current wiring (grounded)

- `build_transition_plan` is defined at `tasks_transition_core.py:173` (keyword-only signature:
  `old_lane, target_lane, force, review_feedback_pointer, arb_review_ref, note_text`). **Note the
  signature carries only the `review_feedback_pointer`/`arb_review_ref` scalars — there is no
  `review_result` param today.** WP02 adds an **optional `review_result` param** (default `None`) as the
  seam WP06 will thread the structured object into; WP02 itself never populates it (the caller
  `tasks_move_task.py:1302` that constructs it is WP06-owned).
- `tasks_transition_core.py:210` — `emit_force = force` (baseline mirrors the `--force` flag).
- `tasks_transition_core.py:218-219` — the bug: `if not force and _is_backward_transition(old_lane,
  canonical_lane): emit_force = True`. Lines 220-230 then synthesise the `"backward rewind: <old> ->
  <new>"` reason.
- `_is_backward_transition` is **imported at `tasks_transition_core.py:57`** from
  `tasks_finalize_validation` (it is NOT defined locally; the spec's "line 384" for it is stale).
- `_guard_subtasks` is defined at `tasks_transition_core.py:384`. It does **not** call
  `tasks_shared._check_unchecked_subtasks` directly — it reads the precomputed
  `req.unchecked_subtasks` tuple (a `MoveTaskRequest` field declared at
  `tasks_transition_core.py:114`). It short-circuits when `req.target_lane not in _REVIEW_GATE_LANES or
  req.force` (`:385`), returns `None` on an empty tuple (`:387`), else builds the refusal
  (`:389-395`).
- The tuple is populated **upstream** in `tasks_move_task.py:505-508` via
  `_tasks._check_unchecked_subtasks(st.repo_root, st.mission_slug, st.task_id, st.force)` and passed
  into the request at `tasks_move_task.py:539`. That reader (`tasks_shared.py:412`) reads `tasks.md`
  text (`tasks_shared.py:445`). **Note:** `tasks_move_task.py` and `tasks_shared.py` are NOT owned by
  this WP — WP04/WP06 own the upstream reader re-point. Your job is the `_guard_subtasks` consumer side.
- `validate_transition` is at `transitions.py:68`, signature `(from_lane, to_lane, ctx: GuardContext |
  None = None) -> tuple[bool, str | None]` — no `force` param; force-free legality is expressed
  structurally by the state object's `transition_to`. `ctx` defaults to `GuardContext()` (`:80`).

### Subtask T007: `build_transition_plan` ask-the-FSM force suppression (FR-015)

**Purpose**: Replace the blunt backward-edge auto-force-promotion with an FSM legality query so
evidence-gated review-rejection edges persist an honest, force-free transition.

**Steps**:
1. In `src/specify_cli/cli/commands/agent/tasks_transition_core.py`, first add an **optional
   `review_result` param** (default `None`) to `build_transition_plan`'s keyword-only signature
   (`tasks_transition_core.py:173`) — the seam WP06 threads its structured object into. WP02 leaves it
   `None`. Then locate the auto-promotion at `tasks_transition_core.py:218-219` and replace the
   unconditional `emit_force = True` with the FSM query from `contracts/emit-force.md`:
   ```
   if not force and _is_backward_transition(old_lane, canonical_lane):
       legal_force_free, _ = validate_transition(old_lane, canonical_lane, ctx_with_evidence)
       emit_force = not legal_force_free
   ```
   where `ctx_with_evidence` is a `GuardContext` (`transitions.py:80`) populated with the **plan-layer
   evidence WP02 actually has**: the `reason`/`review_feedback_pointer` (`in_progress→planned`) and
   `arb_review_ref` (`approved→*`). Thread `review_result` into the context too **when supplied**, but in
   WP02 it is always `None` — so the two `in_review→*` edges are FSM-rejected force-free and **stay
   `emit_force = True`** here (honest: WP02 has no valid evidence for them). That is the intended WP02
   behaviour; **WP06** populates `review_result` and flips those two edges force-free. Import
   `validate_transition` from `status.transitions`. Note the query mechanism is edge-agnostic (it asks
   the FSM for *any* backward edge) — WP02 does **not** hard-code a three-edge list; only the *evidence
   it supplies* differs, so the three plan-reachable edges resolve force-free and the two `in_review→*`
   edges do not until WP06 supplies their evidence.
2. Preserve the reason synthesis at `tasks_transition_core.py:220-230` — an honest force-free backward
   transition still carries its `"backward rewind: ..."` reason and any feedback pointer / user note.
   Only the `force` bit changes, not the audit narrative.
3. Preserve the target expansion at `tasks_transition_core.py:232-234`: `transition_targets =
   [canonical_lane]`, expanded via `_lane_targets_for_emit` only `when not emit_force`. Confirm the new
   force-free backward edges do **not** accidentally trigger forward multi-hop expansion (a backward
   edge stays single-hop; add a guard/test if the expansion path is now reachable).
4. Keep genuine-force promotion intact: edges the FSM rejects force-free (leaving terminal
   `done`/`canceled`, and all `for_review→*`/`claimed→*` rewinds per `contracts/emit-force.md`) must
   still set `emit_force = True`.

**Files**: `src/specify_cli/cli/commands/agent/tasks_transition_core.py`.

**Validation checklist**:
- [ ] The **three** plan-reachable edges (`in_progress→planned`, `approved→in_progress`,
      `approved→planned`) resolve `emit_force == False` **at the plan layer** when supplied their
      edge-specific evidence (`reason`/`review_feedback_pointer`, `arb_review_ref`).
- [ ] With `review_result=None` (the WP02 default), the two `in_review→*` edges resolve
      `emit_force == True` (WP06 flips them — not this WP).
- [ ] A genuine-force edge (e.g. leaving `done`) still resolves `emit_force == True`.
- [ ] `build_transition_plan` accepts an optional `review_result` param (default `None`).
- [ ] No hard-coded edge tuple/set/list appears anywhere (grep the diff) — the FSM query is edge-agnostic.
- [ ] The `"backward rewind: ..."` reason is unchanged for the force-free edges.

**Edge cases**: an `in_review→planned` supplied only a **scalar** `reason` (no structured
`review_result`) is FSM-rejected force-free (`wp_state.py:624`) → `emit_force` stays `True` (honest —
the caller did not supply valid evidence; this is exactly WP02's `review_result=None` state for the two
`in_review→*` edges); explicit `--force=True` short-circuits at `tasks_transition_core.py:210` before the
query (unchanged); a forward edge never enters the branch.

### Subtask T008: `_guard_subtasks` re-source to the reduced snapshot (FR-003)

**Purpose**: Make the review-gate refusal decide from the event-sourced `subtasks` slot, not
`tasks.md` bytes — the consumer half of the subtask eviction.

**Steps**:
1. In `tasks_transition_core.py`, `_guard_subtasks` (`:384`) currently reads
   `req.unchecked_subtasks` (`MoveTaskRequest` field, `:114`), which upstream is populated from
   `tasks.md` text. Re-source the guard's notion of "unchecked" to the WP01 reduced-snapshot
   `subtasks` slot: materialise the snapshot for `req.task_id` and compute the incomplete set from the
   slot (a subtask id whose status is not the done-equivalent).
2. Keep the short-circuit at `:385` (`req.target_lane not in _REVIEW_GATE_LANES or req.force`) and the
   empty→`None` pass at `:387`. Keep the refusal string construction (`:389-395`) — only its **source**
   of unchecked ids changes.
3. Do **not** edit `tasks_move_task.py:505-508/539` or `tasks_shared.py:412` — those upstream readers
   are owned by WP04/WP06. If the request object still needs to carry the tuple during the migration
   window, read the snapshot inside the guard and treat `req.unchecked_subtasks` as a fallback behind
   the FR-005 flag (C-001 symmetric-window: a snapshot-first reader never strands a fresh write). Prefer
   snapshot-authoritative; document the fallback lifetime (removed in WP10).

**Files**: `src/specify_cli/cli/commands/agent/tasks_transition_core.py`.

**Validation checklist**:
- [ ] With completion recorded in the snapshot and `tasks.md` checkboxes still unchecked, the guard
      passes (returns `None`) — the SC-003 mechanism.
- [ ] With genuinely-incomplete subtasks (nothing recorded), the guard still refuses with the
      `:389-395` message.
- [ ] The resolution source is the snapshot `subtasks` slot, not a `tasks.md` read (assert via a
      patched/absent `tasks.md`).

**Edge cases**: a WP with zero subtasks in the snapshot → guard passes (nothing to refuse); a target
lane outside `_REVIEW_GATE_LANES` → short-circuit unchanged; `req.force` true → short-circuit unchanged.

### Subtask T009: Re-point plan-level force tests + persisted-force command-layer regression

**Purpose**: Reconcile the existing tests that assert the old false-force behaviour, and add the SC-007
persisted-layer regression through the real move-task entry point.

**Steps**:
1. Re-point (delete-the-assertion-not-the-test) the enumerated plan-level assertions in
   `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py`:
   - `:542` — `assert plan.emit_force is True` in `test_non_force_backward_is_rewound_and_forced`
     (`approved→in_progress`, `force=False` auto-promoted). Flip to `emit_force is False` given
     supplied `review_ref` evidence; keep the `"backward rewind: approved -> in_progress"` reason
     assertion (`:544`). Rename the test to reflect force-free provenance.
   - `:527-528` — `test_for_review_to_in_progress_force_sets_force_override_ref` is an **explicit
     `force=True`** case; it should stay `emit_force is True` (genuine force). Confirm it is not
     collateral-damaged by the T007 change (it short-circuits at `:210`). Leave as a positive control.
   - Leave the already-`False` asserts (`:110`, `:596`, `:711`) as-is or strengthen to cover the new
     force-free backward edges.
2. Re-point `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` (end-to-end via Typer
   `CliRunner`, reading emitted `StatusEvent.force` off `status.events.jsonl`). The backward-rewind
   assertions currently expect `force is True` (`:348,:395,:445,:529,:556`); flip **only the three
   plan-reachable evidence-gated edges** (`in_progress→planned`, `approved→in_progress`,
   `approved→planned`) to `force is False`. **Leave the two `in_review→*` edges asserting `force is
   True`** — WP02 supplies no `review_result`, so they legitimately stay force-stamped until WP06 flips
   them (do not touch those assertions here; WP06 re-points them). Keep the genuine-force edges (`:205`
   and the explicit `--force` `"Force move to ..."` path at `:351-361`) truthy as positive controls.
3. Create `tests/regression/test_2684_force_provenance.py` (SC-007, **WP02 slice = three edges**): drive
   each of the **three** plan-reachable evidence-gated edges through the **real move-task entry point**
   (Typer `CliRunner`, not the plan object), read the **persisted** `StatusEvent.force` off
   `status.events.jsonl`, assert falsy for all three with correct edge-specific evidence, and assert a
   retained genuine-force edge (e.g. leaving `done`) persists `force` truthy (positive control).
   Optionally add the two `in_review→*` edges as **truthful-force controls** for the WP02 window (force
   still truthy because no `review_result` is threaded). **WP06 extends this same file to assert the two
   `in_review→*` edges force-free** once it constructs/threads `review_result` — leave that extension to
   WP06; do not pre-flip them here. Register the `regression` marker per `pytest.ini`.

**Files**: `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py` (re-point),
`tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` (re-point),
`tests/regression/test_2684_force_provenance.py` (new).

**Validation checklist**:
- [ ] No re-pointed test was **deleted** — only its expected value corrected (the tests still exist and
      still assert force provenance).
- [ ] The new regression reads persisted force from the jsonl, not from the plan object.
- [ ] Each of the **three** plan-reachable edges is supplied its correct evidence type and asserts force
      falsy; the two `in_review→*` edges (no `review_result` in WP02) are left/asserted force-truthy as
      the WP02-window control, with their force-free flip deferred to WP06.

**Edge cases**: an edge that is force-free-legal but where the caller omits evidence → persisted `force`
truthy (honest); the genuine-force positive control must fail loudly if T007 over-suppresses.

## Branch Strategy

- **Planning base branch**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Final merge target**: `mission-prep/2684-wp-runtime-state-eviction`.
- **Strategy**: `lane-per-wp`. Execution worktrees allocated per computed lane from `lanes.json`.
  **Land order**: WP02 depends on WP01 and MUST land before the writer WPs (WP04/WP06/WP07/WP08/WP09).
  The reason is **logical dependency, not a merge race**: WP02 owns `tasks_transition_core.py` alone, so
  there is no shared-file contention to avoid (the "avoid `tasks_transition_core.py`/
  `tasks_move_task.py`/`emit.py` merge races" rationale in the older land-order note is factually wrong —
  those files are owned by *different* WPs and never co-edited). The real reason is that WP04 and WP06
  build **on top of** WP02's corrected force-provenance and re-sourced subtask gate: WP06 threads
  `review_result` into the seam WP02 adds and extends SC-007 to the two `in_review→*` edges, and the
  writer WPs must rebase onto the corrected force logic so they never re-introduce the false-force stamp.
  Landing WP02 first means everyone downstream starts from honest force provenance rather than patching
  it afterward.

## Definition of Done

- [ ] `build_transition_plan` gains an optional `review_result` param (default `None`) as the seam WP06
      threads into; WP02 never populates it (T007).
- [ ] `build_transition_plan` suppresses `emit_force` on the **three plan-reachable** FSM-legal-force-free
      backward edges (`in_progress→planned`, `approved→in_progress`, `approved→planned`) via the
      `validate_transition` query, with **no** hard-coded edge list; the two `in_review→*` edges stay
      force-truthy under WP02 (no `review_result`) and are WP06's to flip (FR-015, T007).
- [ ] Edge-specific evidence flows into the FSM context; genuine-force edges stay truthy (T007).
- [ ] `_guard_subtasks` decides from the reduced-snapshot `subtasks` slot and still refuses
      genuinely-incomplete WPs (FR-003, T008).
- [ ] The enumerated plan-level force tests are **re-pointed, not deleted** (SC-007, T009).
- [ ] `tests/regression/test_2684_force_provenance.py` asserts persisted `StatusEvent.force` falsy for
      the **three** plan-reachable edges + a genuine-force positive control, via the real move-task path;
      the two `in_review→*` edges remain force-truthy controls in the WP02 window, with **WP06 extending
      SC-007 to all five** (SC-007/NFR-003).
- [ ] `pytest tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
      tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py
      tests/regression/test_2684_force_provenance.py`, `ruff check`, and `mypy` on the module are green.
- [ ] No changes outside `owned_files` (in particular: no edits to `tasks_move_task.py`,
      `tasks_shared.py`, or `transitions.py`).

## Risks

- **Hard-coding an edge list.** The single biggest anti-pattern here; the design explicitly forbids it
  because the matrix can change. Ask the FSM. The query is edge-agnostic — WP02 covers the three
  plan-reachable edges purely by *which evidence it supplies*, never by enumerating edges.
- **Over-suppression.** If `ctx_with_evidence` is under-populated, a genuinely-force edge could go
  force-free (silent provenance loss the other way). The genuine-force positive control guards this —
  keep it.
- **Evidence type confusion.** `in_review→*` needs a structured `review_result`, not a scalar reason
  (`wp_state.py:624`). In WP02 that object is never supplied (it is WP06's to construct/thread), so those
  two edges stay force-truthy — *correct* for the WP02 window, but easy to misread as a bug or to "fix"
  by over-suppressing. Do not flip them here; leave them to WP06. Test that they stay truthy under WP02.
- **Cross-file bleed.** The subtask reader lives upstream in files this WP does not own. Re-source the
  **consumer** (`_guard_subtasks`) only; do not touch `tasks_move_task.py`/`tasks_shared.py`.

## Reviewer guidance

- Grep the diff for any literal set/list of lane pairs (three or five) — its presence is an automatic
  reject; the FSM query must stay edge-agnostic.
- Confirm WP02 flips exactly the **three** plan-reachable edges and leaves the two `in_review→*` edges
  force-truthy (no `review_result` populated) — flipping them here is out of scope (WP06 owns it).
- Confirm the persisted-force regression reads `status.events.jsonl`, not `plan.emit_force`.
- Confirm the re-pointed tests still assert provenance (they were corrected, not gutted) — count
  assertions before/after.
- Confirm `_guard_subtasks` reads the snapshot with `tasks.md` absent/patched and still refuses a
  genuinely-incomplete WP.
- Confirm no edits leaked into `tasks_move_task.py`, `tasks_shared.py`, or `transitions.py`.
- Confirm the genuine-force positive control fails if force is over-suppressed (non-vacuous).

## Activity Log

- 2026-07-19T10:49:48Z – claude:opus:python-pedro:implementer – shell_pid=2440108 – Assigned agent via action command
- 2026-07-19T11:19:57Z – claude:opus:python-pedro:implementer – shell_pid=2440108 – Ready: 3-edge force fix + flag-gated _guard_subtasks; force tests re-pointed, persisted-force regression green
- 2026-07-19T11:21:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=2548429 – Started review via action command
- 2026-07-19T11:25:54Z – user – shell_pid=2548429 – Review passed: ask-the-FSM force fix is edge-agnostic (no hard-coded edge list; validate_transition query on 3 plan-reachable edges), optional review_result seam added (default None). _guard_subtasks re-sourced to WP01 snapshot subtasks slot, flag-gated behind _phase1_dual_write_enabled with legacy fallback, refusal branch intact. Tests re-pointed not deleted; genuine-force positive controls kept; dropped fixture force cross-check is genuinely superseded (approved->planned force=False now asserted directly in 3 places; Mission-1 fixture is a stale immutable snapshot). Regression reads persisted status.events.jsonl via real move-task. approved->in_progress plan-layer force-free proof honest; CLI-layer truthfully force per WP02/WP06 split. Scope clean (4 owned files only). 76 passed, ruff+mypy green.
