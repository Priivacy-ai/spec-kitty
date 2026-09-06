---
work_package_id: WP01
title: Production fix — Lane.UNINITIALIZED guard + coord-topology reachability anchoring
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-009
- FR-010
planning_base_branch: fix/runtime-advance-guard-3883
merge_target_branch: fix/runtime-advance-guard-3883
branch_strategy: "single_branch topology (per meta.json): this mission has no coordination branch, no per-WP branches, and no worktrees. All planning and implementation happen directly on fix/runtime-advance-guard-3883, the mission's one and only branch. planning_base_branch and merge_target_branch both name that same branch because there is no separate landing/merge step for this WP -- committed changes land on fix/runtime-advance-guard-3883 directly."
base_branch: kitty/mission-runtime-advance-guard-topology-wp-completion-01M1W6VZ
base_commit: ffa5012918af36d2793b825b58cc27f9ee2d49dc
created_at: '2026-09-07T02:25:05.689998+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
- T013
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- tests/runtime/next/test_advance_guard_uninitialized_wp.py
- tests/runtime/next/test_advance_guard_coord_reachability.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/runtime/next/test_advance_guard_uninitialized_wp.py
- tests/runtime/next/test_advance_guard_coord_reachability.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Land #3884's fix in full: `_wp_blocks_step`'s `Lane.UNINITIALIZED` disjunct
(FR-004/005), `_should_advance_wp_step`'s coord-topology reachability anchoring
extension (FR-009), and the one new fail-loud catch arm that anchoring extension
requires (FR-010) — as ONE work package, in ONE source file
(`src/runtime/next/runtime_bridge.py`), with every named red-first reproduction the
plan's Test Strategy requires.

## Context

**This mission was narrowed by operator ruling on 2026-09-07** from two issues
(#3883 + #3884) down to #3884 only. See `spec.md`'s "Scope Narrowing" section and
`plan.md`'s "Narrowing" section (appended after the preserved round-history) for the
full evidence: draft PR #3923 already fixes #3883 independently in
`runtime_bridge_io.py`, a file this WP does **not** touch (the pre-narrowing draft
of this WP owned `runtime_bridge_io.py` and `runtime_bridge_composition.py` too —
neither is in this WP's `owned_files` any more).

**The established mechanism (settled, not re-derived here).** A work package file
under `tasks/` that was never claimed folds to `Lane.UNINITIALIZED` forever
(`committed_authority.wp_ending`, `src/runtime/next/committed_authority.py:102-133`).
`_wp_blocks_step("implement", state, has_provenance)`
(`runtime_bridge.py:781-810`) currently falls through both disjuncts of its
`implement`-branch return expression for this state and returns `False` (does not
block) — by omission, not by any deliberate "this is fine" decision. Fixing that
function alone is **not sufficient**: `_should_advance_wp_step`
(`runtime_bridge.py:738-780`), the caller that must reach `_wp_blocks_step`'s per-WP
loop in the first place, does its OWN separate, unanchored `tasks_dir = feature_dir
/ "tasks"` read (`:753`) — for a real coord-topology mission this hits the
function's own no-`tasks/`-dir early return (`:754-755`) and returns `True`
unconditionally, before the per-WP loop is ever reached, regardless of whether
`_wp_blocks_step`'s own fix has landed. This WP ships both fixes together, plus the
one new exception-handling arm the anchoring extension introduces (FR-010).

**Why FR-010 targets `MissionSelectorAmbiguous`, not a new exception class —
verified empirically during the narrowing, cite this rather than re-deriving it.**
`mission_runtime.placement_seam(repo_root, mission_slug).read_dir(
MissionArtifactKind.WORK_PACKAGE_TASK)` resolves a PRIMARY-partition kind's
directory via pure path composition off the canonicalized `mission_slug`
(`resolve_artifact_surface`'s own docstring: "a PRIMARY-partition kind resolves the
primary mission dir... for EVERY topology and coord state — it never transits
coord"), never a `meta.json` content read — empirically confirmed against this
checkout: a nonexistent mission slug resolves to a real (if absent) `Path`, no
raise. The ONE exception this call can genuinely raise is `MissionSelectorAmbiguous`
(`src/specify_cli/missions/_read_path_resolver.py:44`), for a genuinely ambiguous
handle — already imported the same way in several places inside
`src/mission_runtime/resolution.py` itself. Do not invent a new exception class; do
not assume a corrupt-`meta.json` fixture will raise here (it will not, for this
kind).

**This WP depends on WP02** for its coord-topology fixture and the
`feature_dir.name`→`mission_slug` empirical finding — import
`build_coord_topology_fixture` from `tests/runtime/next/test_coord_topology_fixture.py`
(or the shared fixture location WP02 actually settled on — check its completion
notes/docstring) rather than re-building an equivalent fixture from scratch. WP02's
builder is parameterized on `wp_events`; this WP calls it with the default (empty —
folds to `UNINITIALIZED`) rather than WP02's own `in_progress` variant.

**Owned test files, and why there are two, neither overlapping WP02's.**
`tests/runtime/next/test_advance_guard_uninitialized_wp.py` (the direct +
non-coord end-to-end reproduction, FR-004/005) and
`tests/runtime/next/test_advance_guard_coord_reachability.py` (the coord-topology
end-to-end reproduction proving FR-004+FR-009 together, the FR-010 raise-and-catch
reproduction, and the no-op regression pins) are both new files owned exclusively by
this WP — neither name overlaps WP02's `test_coord_topology_fixture.py` at the file
or glob level, so `owned_files` stays pairwise disjoint across all three WPs even
though this WP imports from WP02's file.

**Baseline-red discipline applies to every subtask that runs tests, not only the
final validation pass.** `main` carries pre-existing known-red tests per CLAUDE.md
(#2736, #2772, #1834). Whenever you run a test in this WP and see a failure you did
not expect, classify it before assuming it is yours: (1) pre-existing known-P0 red
(confirm by running the same test against `upstream/main`/the merge-base), (2) a
CI-environment failure, (3) a stale-install false red, or (4) a stale-venv false red
(re-run `uv sync --frozen --all-extras` before recording it as pre-existing). Only a
failure that is red on this branch AND green on `main` at the same commit is this
WP's to fix.

**Tracer files.** `tracer-*.md` are owned by WP03 in `wps.yaml`. If you want to
record an implementation-time design note, that is a small, well-justified
out-of-map edit under this repo's ownership-map leeway norm — record a one-line
rationale, do not add these files to this WP's own `owned_files`.

---

## Subtask T006: `_wp_blocks_step` — the `Lane.UNINITIALIZED` disjunct (FR-004/005)

**Purpose**: Close #3884 at its root: a WP scaffolded under `tasks/` but never
claimed (`Lane.UNINITIALIZED`) currently falls through both existing disjuncts of
the `implement` branch's return expression and is silently treated as "does not
block" by omission, not by any deliberate decision.

**Steps**:
1. In `src/runtime/next/runtime_bridge.py:781-810`, locate the `implement` branch
   (`:799-807`):
   ```python
       if step_id == "implement":
           return (
               state.is_blocked
               or (state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED))
           )
   ```
2. Replace with the minimal, additive fix — one new disjunct, no restructuring:
   ```python
       if step_id == "implement":
           # Advance past implement only when the WP has been handed off
           # (for_review or approved) or reaches an acceptable ending.
           # is_run_affecting is True for all active lanes; we further restrict
           # to only allow advancement for the "handed off" active lanes.
           # FR-004 (#3884): Lane.UNINITIALIZED is neither is_blocked nor
           # is_run_affecting (it never entered an active lane) -- it fell
           # through both disjuncts and silently did not block. A never-claimed
           # WP must not be conflated with a genuinely-exempt state.
           return (
               lane is Lane.UNINITIALIZED
               or state.is_blocked
               or (state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED))
           )
   ```
3. Do NOT touch: the `is_acceptable_ending(...)` early-return (`:794-798`,
   untouched — `UNINITIALIZED` never satisfies it) or the `review` branch
   (`:808-809`, untouched — this is an `implement`-only fix).

**Files**: `src/runtime/next/runtime_bridge.py` (~3 lines changed).

**Validation**: Covered by T007's direct-call assertion.

## Subtask T007: Reproduction — direct + non-coord end-to-end (FR-004/005)

**Purpose**: The red-first reproduction for #3884's `_wp_blocks_step` fix, written
against the function's CURRENT, plain 2-arg `_should_advance_wp_step` signature
only — no directory I/O, no `placement_seam`, no coord-topology fixture, so it has
zero dependency on WP02's coord fixture (only on WP02's WP itself finishing first,
per the `dependencies: [WP02]` edge).

**Steps** (write in `tests/runtime/next/test_advance_guard_uninitialized_wp.py`):
1. Construct a WP file under a plain `tasks/` directory (a non-coord fixture whose
   `feature_dir` directly contains `tasks/`) with zero lane-transition events for
   that WP id, so `committed_authority.wp_ending` folds it to `WpEnding(lane=
   "uninitialized", acceptable=False, reason_source=None)`.
2. Direct call: `_wp_blocks_step("implement", UninitializedState(), has_provenance=False)`
   — assert `True` (post-fix) — this is the isolated direct-call test Sonar coverage
   attribution needs.
3. End-to-end assertion (AC-2): `_should_advance_wp_step("implement", feature_dir)`
   — **no `repo_root`/`mission_slug` keywords** — returns `False` for the mission as
   a whole, using the non-coord fixture from step 1.
4. Regression pins, **UN-anchored case only** (the "anchored" variant lives in T012,
   since it needs T008's extended signature): call `_should_advance_wp_step(
   "implement", feature_dir)` (2-arg only) against (a) a fixture with genuinely no
   `tasks/` directory — assert it still returns `True` (AC-3, the legitimate no-op
   case, untouched by this fix); and (b) confirm the `except ValueError` block
   (`runtime_bridge.py:768-773`) does not fire for `"uninitialized"` (AC-4) — e.g.
   by asserting no exception propagates and the WP's folded state is genuinely
   `UninitializedState`, not a `ValueError`-triggered fallback.

**Files**: `tests/runtime/next/test_advance_guard_uninitialized_wp.py` (~90 lines).

**Validation**: RED against unmodified `_wp_blocks_step` (step 2's assertion fails,
showing `False` instead of `True`); GREEN once T006 lands.

## Subtask T008: `_should_advance_wp_step` — the FR-009 anchoring extension

**Purpose**: Without this, T006's `Lane.UNINITIALIZED` fix is structurally inert for
a real COORD-topology mission — `_should_advance_wp_step`'s own unanchored
`tasks_dir = feature_dir / "tasks"` read (`:753`) hits its early return and returns
`True` before the per-WP loop that calls `_wp_blocks_step` is ever reached.

**Steps**:
1. In `src/runtime/next/runtime_bridge.py`, extend `_should_advance_wp_step`'s
   signature with two new keyword-only parameters, gated on `repo_root is not
   None` (no separate flag — mirrors the #3704 precedent already established
   elsewhere in this call graph):
   ```python
   def _should_advance_wp_step(
       step_id: str,
       feature_dir: Path,
       *,
       repo_root: Path | None = None,
       mission_slug: str | None = None,
   ) -> bool:
       anchor_dir = feature_dir
       if repo_root is not None:
           from mission_runtime import MissionArtifactKind, placement_seam  # noqa: PLC0415 — matches this module's existing deferred-import idiom at :265-275/:1535

           resolved_mission_slug = mission_slug if mission_slug is not None else feature_dir.name
           anchor_dir = placement_seam(repo_root, resolved_mission_slug).read_dir(
               MissionArtifactKind.WORK_PACKAGE_TASK
           )
       tasks_dir = anchor_dir / "tasks"
       if not tasks_dir.is_dir():
           return True  # no WPs to iterate over
       wp_files = sorted(tasks_dir.glob(TASKS_GLOB))
       if not wp_files:
           return True
       ...
       for wp_file in wp_files:
           ...
           ending = committed_authority.wp_ending(feature_dir, wp_id)  # UNCHANGED —
           # WP-lane state is a coord-partition (status.events.jsonl) read; it stays
           # on feature_dir even after anchoring tasks_dir to primary.
   ```
   **No shared helper is extracted** — `placement_seam`/`MissionArtifactKind` are
   already imported the same way elsewhere in this module (`:265-275`, `:1535`);
   there is exactly one caller of this anchoring logic now that #3883's own
   (now-deleted) `gather_artifact_presence` anchoring is out of scope, so inlining
   it here is correct, not a DIRECTIVE_044 violation — extracting a helper for a
   single caller would be the wrong direction.
2. Thread `repo_root=repo_root, mission_slug=mission_slug` into
   `_should_advance_wp_step`'s ONE genuinely load-bearing production call site —
   `_dn_dependency_gate`'s WP-iteration branch, direct call at `:1680`:
   ```python
           should_advance = _should_advance_wp_step(
               current_step_id, feature_dir, repo_root=repo_root, mission_slug=mission_slug
           )
   ```
   `mission_slug`/`repo_root` are already local variables in this exact function
   (`mission_slug = ctx.mission_slug` at `:1667`, `repo_root = ctx.repo_root` at
   `:1670`, both bound before line 1680) — no new resolution needed.
3. **Do NOT thread this into `_check_cli_guards:858`'s own internal
   `_should_advance_wp_step` call, and do NOT touch
   `runtime_bridge_composition.py:557`'s call.** This is a deliberate, proven
   scope boundary, not an oversight — see `plan.md`'s "Explicitly not touched"
   section for the full control-flow trace: both of those calls are only ever
   reached AFTER the `:1680` call (this subtask's own edit) has already succeeded
   with the identical `feature_dir`/`repo_root`/`mission_slug` inputs and no
   intervening filesystem mutation, so anchoring them too would be provably inert
   duplication, not a functional requirement. If you find yourself tempted to
   "also fix" those two call sites for symmetry, don't — it would touch a second
   file (`runtime_bridge_composition.py`) this mission's own narrowing keeps out
   of scope, for zero behavioral benefit.
4. Do not touch the no-`tasks/`-dir early-return logic itself or the `except
   ValueError` block (`runtime_bridge.py:768-773`) — only WHICH directory
   `tasks_dir` is computed from changes.

**Files**: `src/runtime/next/runtime_bridge.py` (~15 lines: signature + anchoring
body + 1 call-site edit).

**Validation**: Covered by T010's reproduction and T012's anchored no-op pins.

## Subtask T009: FR-010 — the one new catch arm

**Purpose**: `_should_advance_wp_step` can now raise `MissionSelectorAmbiguous` (via
T008's anchoring, for a genuinely ambiguous `mission_slug` handle) at its one real
call site. An uncaught crash out of `decide_next_via_runtime` is not acceptable
behavior for this failure class — mirror the codebase's own established precedent
one line above.

**Steps**:
1. Add the import near the top of `src/runtime/next/runtime_bridge.py`, alongside
   the existing `from specify_cli.status import CanonicalStatusNotFoundError`
   (`:181`):
   ```python
   from specify_cli.missions._read_path_resolver import MissionSelectorAmbiguous
   ```
2. In `_dn_dependency_gate`'s WP-iteration branch (`runtime_bridge.py:1678-1697`),
   add a sibling `except` arm immediately after the existing
   `except CanonicalStatusNotFoundError as exc:` block, constructing the identical
   `blocked` Decision shape:
   ```python
           try:
               should_advance = _should_advance_wp_step(
                   current_step_id, feature_dir, repo_root=repo_root, mission_slug=mission_slug
               )
           except CanonicalStatusNotFoundError as exc:
               return _materialize_decision(
                   _cores.DecisionEnvelope(
                       kind=DecisionKind.blocked,
                       agent=agent, mission_slug=mission_slug, mission=mission_type,
                       mission_state=current_step_id, timestamp=now, reason=str(exc),
                       progress=progress, origin=origin, run_id=run_ref.run_id,
                       step_id=current_step_id,
                   ),
                   [str(exc)],
               )
           except MissionSelectorAmbiguous as exc:  # NEW — FR-010
               return _materialize_decision(
                   _cores.DecisionEnvelope(
                       kind=DecisionKind.blocked,
                       agent=agent, mission_slug=mission_slug, mission=mission_type,
                       mission_state=current_step_id, timestamp=now, reason=str(exc),
                       progress=progress, origin=origin, run_id=run_ref.run_id,
                       step_id=current_step_id,
                   ),
                   [str(exc)],
               )
   ```
3. No other catch site is needed — see T008 step 3's proof that `_check_cli_guards:858`
   and `_check_composed_action_guard:557` never independently trigger this raise in
   production.

**Files**: `src/runtime/next/runtime_bridge.py` (~15 lines: 1 import + 1 new
`except` arm).

**Validation**: Covered by T011's reproduction.

## Subtask T010: Reproduction — coord-topology end-to-end (FR-004+FR-009 together)

**Purpose**: Prove FR-004's fix genuinely fires for the production scenario this
mission exists to fix — not just at the `_wp_blocks_step` unit level (T007 alone is
necessary but not sufficient proof), and not only in isolation as WP02's own T003
proved FR-009 alone (that reproduction deliberately used an `in_progress` WP to
avoid conflating the two bugs — this one deliberately uses an uninitialized WP to
prove they resolve TOGETHER for the real #3884 scenario).

**Steps** (write in `tests/runtime/next/test_advance_guard_coord_reachability.py`):
1. Reuse WP02's coord-topology fixture builder (`build_coord_topology_fixture` or
   equivalent) with its DEFAULT `wp_events` (empty — folds to `UNINITIALIZED`), NOT
   WP02's own `in_progress` variant: primary dir with a real `tasks/WP01-*.md` for a
   WP with zero lane-transition events, coord-worktree `feature_dir` holding only
   `status.events.jsonl`.
2. As soon as T008's signature extension lands (parameters accepted, anchoring body
   not yet applied — i.e., write this test immediately after T008's signature
   change, before its body change, if you are sequencing commits granularly; if you
   land T008 as one commit, write and confirm this assertion is what T008's own
   body makes pass, and separately confirm by temporarily reverting T006 that the
   test fails without it too, to prove BOTH fixes are load-bearing): call
   `_should_advance_wp_step("implement", coord_feature_dir, repo_root=<repo_root>,
   mission_slug=<slug>)` and assert it returns `False` — the coord-anchored answer.
3. Also assert the parallel primary-dir call (`_should_advance_wp_step("implement",
   primary_dir)`, no anchoring keywords needed since it's already the primary
   checkout) returns the same `False` — confirming the coord-anchored answer agrees
   with the already-correct primary-direct answer.
4. In your completion notes, record explicitly that this reproduction requires BOTH
   T006 (the `Lane.UNINITIALIZED` disjunct) AND T008 (the anchoring extension) to be
   in place — reverting either one alone should make this test fail, which is the
   proof that the two fixes are genuinely joint, not merely coincidentally both
   present.

**Files**: `tests/runtime/next/test_advance_guard_coord_reachability.py` (~40
lines).

**Validation**: Fails if either T006 or T008 alone is reverted; passes once both are
in place.

## Subtask T011: Reproduction — FR-010 raise-and-catch

**Purpose**: Drive a genuine `MissionSelectorAmbiguous` failure through the one real
catch site T009 adds, with real failure injection — never a monkeypatched
exception standing in for behavior that was never verified to occur.

**Steps** (write in `tests/runtime/next/test_advance_guard_coord_reachability.py`):
1. Build a fixture with two (or more) mission directories under a `kitty-specs/`-shaped
   tree sharing a common prefix, such that a `mission_slug` value matching that
   prefix non-uniquely makes
   `placement_seam(repo_root, mission_slug).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)`
   raise `MissionSelectorAmbiguous` for real (not via `unittest.mock.patch`) —
   confirm this raises directly, in isolation, before wiring it into the full
   `_dn_dependency_gate` call in step 2.
2. Construct a `rb.DecideNextContext` by hand (`current_step_id="implement"`,
   `result="success"`, `feature_dir=` the ambiguous fixture's coord-shaped dir,
   `repo_root=` the fixture's `repo_root`, `mission_slug=` the ambiguous prefix),
   following `tests/runtime/next/test_cli_guard_family.py:487`'s
   `test_cli_pre_check_threads_real_repo_root` construction pattern.
3. Call `rb._dn_dependency_gate(ctx)` directly and assert a `DecisionKind.blocked`
   Decision whose `reason` contains the exception's message — RED (an uncaught
   `MissionSelectorAmbiguous` propagates) before T009's `except` arm lands, GREEN
   after.

**Files**: `tests/runtime/next/test_advance_guard_coord_reachability.py` (~40
lines).

**Validation**: RED before T009, GREEN after.

## Subtask T012: No-op regression pins

**Purpose**: Satisfy the charter's 90%+ new-code coverage floor
(`.kittify/charter/charter.md:262`) for the anchoring's negative-space paths — the
cases where anchoring must NOT change behavior.

**Steps** (write in `tests/runtime/next/test_advance_guard_coord_reachability.py`):
1. **`single_branch` no-op pin**: call `_should_advance_wp_step` with `repo_root`
   set for THIS mission's own `single_branch`-topology checkout (this repo IS
   `single_branch` — a live dogfood fixture, not a synthetic one) and assert the
   return value is unchanged from the un-anchored 2-arg call.
2. **Anchored no-`tasks/`-dir no-op pin**: a parallel assertion for the legitimate
   no-`tasks/`-dir case (a `plan`-family-shaped fixture, or any fixture with
   genuinely no `tasks/` directory on primary) with `repo_root` set, asserting it
   still returns `True` — the anchoring is a no-op in both cases (this is the
   "anchored" completion of AC-3, which T007's un-anchored pin left deliberately
   incomplete).

**Files**: `tests/runtime/next/test_advance_guard_coord_reachability.py` (~30
lines).

**Validation**: Both assertions pass once T008 lands; run them individually to
confirm each exercises the specific branch it targets.

## Subtask T013: Self-validation — lint, targeted tests, tracer note

**Purpose**: Confirm this WP's diff is clean before it is handed to review.

**Steps**:
1. Run `ruff check` and `mypy` against `src/runtime/next/runtime_bridge.py`, zero
   issues/warnings, no new suppressions (per CLAUDE.md Code Style — fix the code, do
   not suppress).
2. Run this WP's own new test files (`test_advance_guard_uninitialized_wp.py`,
   `test_advance_guard_coord_reachability.py`) plus WP02's file
   (`test_coord_topology_fixture.py`) together — confirm all reproductions are
   GREEN post-fix (not merely RED-then-untested).
3. Run this mission's blast-radius shards (`tests/runtime tests/runtime/next
   tests/next tests/specify_cli/next tests/specify_cli/status`) and confirm no new
   red relative to `main`/`upstream/main` at the same commit, classifying anything
   unexpected per the baseline-red gotcha before assuming it is this WP's fault.
   Record the exact invocations and pass counts in your own WP completion notes
   (WP03 re-runs the NFR-001-exact invocations independently — this step is your
   own self-check, not a substitute for that).
4. If you resolved any detail differently than this prompt anticipated (e.g., a
   different exact line for the catch-site edit, since T006/T008/T009 will have
   shifted some line numbers within `runtime_bridge.py`), note the as-implemented
   line numbers in your completion notes so WP03 and any reviewer has an accurate
   map.

**Files**: none new — validation only.

**Validation**: `spec-kitty agent tasks mark-status T00N --status done` for each of
T006–T013.

## Definition of Done

- `src/runtime/next/runtime_bridge.py` carries the changes described in T006/T008/T009,
  with zero ruff/mypy issues and zero new suppressions.
- Both new test files (`test_advance_guard_uninitialized_wp.py`,
  `test_advance_guard_coord_reachability.py`) exist, and every reproduction named in
  plan.md's Test Strategy (items 1/2/3/4, this WP's scope) passes GREEN against this
  WP's own final diff.
- T010's coord-topology reproduction fails if either T006 or T008 alone is
  reverted — the joint-fix proof is explicit, not assumed.
- **Baseline-red discipline** (see Context above): every test-run classified before
  being folded into this WP's own pass/fail accounting; no pre-existing red
  (#2736, #2772, #1834) misattributed to this diff.
- `spec-kitty agent tasks mark-status T00N --status done` recorded for each of
  T006–T013.

## Risks

- **PR #3923 (open, draft, base=`main`) independently fixes #3883 in
  `runtime_bridge_io.py` — this mission does not touch that file at all, so there
  is no landing-order conflict with it.** Re-confirmed as of the 2026-09-07
  narrowing: `gh pr view 3923 --json state,isDraft,baseRefName` — still
  OPEN/DRAFT/base=`main`. Since this WP's `owned_files` no longer include
  `runtime_bridge_io.py`, whether PR #3923 merges before, during, or after this
  mission has no bearing on this WP's diff. If a future reviewer somehow finds this
  WP touching `runtime_bridge_io.py`, that is itself a scope regression — flag it.
- **Line-number drift across subtasks within this same WP**: T006/T008/T009's
  edits to `runtime_bridge.py` will shift some of the exact line numbers plan.md
  cites (all citations above were verified against the pre-this-WP checkout).
  Re-verify each cited line against the live file state at the point you make each
  edit.
- **Temptation to "also fix" `_check_cli_guards`/`_check_composed_action_guard` for
  symmetry**: do not. T008 step 3 documents the proof that this would be inert
  duplication touching a second file this mission's narrowing keeps out of scope.

## Reviewer Guidance

- Confirm the `owned_files` boundary was respected: no edits outside the three
  files this WP owns (`runtime_bridge.py` and the two new test files) — in
  particular, confirm `runtime_bridge_io.py` and `runtime_bridge_composition.py`
  are untouched.
- Confirm T008's anchoring is threaded into exactly ONE call site
  (`_dn_dependency_gate`'s WP-iteration branch, `:1680`) and NOT into
  `_check_cli_guards:858` or `runtime_bridge_composition.py:557` — cross-check
  against plan.md's "Explicitly not touched" proof if this is unclear.
- Confirm T009's new `except MissionSelectorAmbiguous` arm is a sibling to the
  existing `except CanonicalStatusNotFoundError` arm, not a replacement of it.
- Confirm T010's reproduction genuinely fails when either T006 or T008 is
  individually reverted (ask the implementer to demonstrate this, or verify by
  temporarily reverting each in a scratch checkout) — this is the mission's own
  proof that the two fixes are joint, not merely both present.
- Confirm T011's `MissionSelectorAmbiguous` fixture is a REAL ambiguous-slug
  fixture, not a monkeypatch standing in for a failure mode that was never
  independently verified to occur.
- Confirm zero ruff/mypy suppressions were added to make this diff pass.

**Implementation command**: `spec-kitty agent action implement WP01 --agent claude`
