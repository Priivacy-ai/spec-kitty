# Implementation Plan: Runtime Advance Guard — Uninitialized-WP Completion

**Branch**: `fix/runtime-advance-guard-3883` | **Date**: 2026-09-06 (narrowed 2026-09-07) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/spec.md`

**Note**: This mission is already on its feature branch (`fix/runtime-advance-guard-3883`,
topology `single_branch`) — that decision was made at `mission create` time and is not
revisited here.

**Narrowing notice (2026-09-07, operator ruling) — read before the rest of this
document.** This plan originally covered two issues (#3883's `gather_artifact_presence`
topology anchoring, "Seam 1" below, and #3884's `_wp_blocks_step`/`_should_advance_wp_step`
fix, "Seam 2" below) across six adversarial review rounds. The operator has ruled #3883 out
of scope: draft PR #3923 already fixes it via an independently-invented, further-progressed
kind-aware placement seam in the same file (`runtime_bridge_io.py`) this plan's own Seam 1
would have edited. **Seam 1 is deleted from this plan's body below** — see spec.md's own
"Scope Narrowing" section and this document's new final "Narrowing" section (appended after
the preserved round-history sections) for the full evidence and the one new empirical finding
this narrowing work produced. Seam 2 (`_wp_blocks_step`) and Seam 2's own reachability
extension (now promoted to spec.md as FR-009/FR-010) both survive, largely unchanged in
substance — they never depended on Seam 1's `resolve_primary_anchor_dir`/
`PrimaryPlacementResolutionError` design being real, only on the SHAPE of that design
existing somewhere reachable from `runtime_bridge.py`; this plan now shows Seam 2's own
extension resolving that shape directly, inline, using the SAME already-existing
`mission_runtime.placement_seam` primitive `runtime_bridge.py` already imports elsewhere for
an unrelated read (`_mission_routes_through_coordination`, `:265-275`) — not a new helper of
this mission's own invention. **All line citations below were re-verified against the live
checkout on 2026-09-07** (not trusted from the pre-narrowing draft) unless explicitly marked
otherwise.

## Summary

One defect remains in scope after the operator's 2026-09-07 narrowing (see above):

- **#3884 (FR-004/005/009/010)**: `_wp_blocks_step("implement", state, ...)`
  (`src/runtime/next/runtime_bridge.py:781-810`) silently permits advancement past
  `implement` for a work package that was scaffolded under `tasks/` but never claimed
  (`Lane.UNINITIALIZED`) — because `UninitializedState` is neither `is_blocked` nor
  `is_run_affecting`, it falls through both disjuncts of the `implement` branch's
  `return` expression and the function returns `False` (does not block) by omission,
  not by a deliberate "this is fine" decision anywhere in the code (FR-004/005). **This
  fix alone is unreachable for a real COORD-topology mission** unless
  `_should_advance_wp_step` — the caller that must reach `_wp_blocks_step`'s per-WP loop
  in the first place — is also anchored on the mission's primary placement (FR-009), with
  the one resulting new failure mode (an ambiguous `mission_slug`) caught at its one real
  call site rather than left to crash `decide_next_via_runtime` (FR-010). This plan ships
  all four together for exactly that reason.

`#3883` (the former User Story 1 — `gather_artifact_presence`'s own topology anchoring in
`runtime_bridge_io.py`) is out of scope; see the Narrowing notice above.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase, no new runtime dependency)
**Primary Dependencies**: `mission_runtime.placement_seam` / `mission_runtime.MissionArtifactKind`
(already a live import elsewhere in `runtime_bridge.py` — no new package dependency, no new
inter-module boundary edge); `specify_cli.missions._read_path_resolver.MissionSelectorAmbiguous`
(an existing exception class, imported the same way `mission_runtime/resolution.py` itself
already imports it in several places — no new exception type is introduced by this mission)
**Storage**: N/A — filesystem presence checks only, no schema/DB change
**Testing**: pytest, existing `tests/runtime/`, `tests/runtime/next/`, `tests/next/`,
`tests/specify_cli/next/`, `tests/specify_cli/status/` suites; new red-first tests
added under `tests/runtime/next/`
**Target Platform**: spec-kitty CLI runtime (Linux/macOS/Windows dev hosts + CI)
**Project Type**: single project (Python package, `src/` layout)
**Performance Goals**: no change — this adds one `Path` resolution + a bounded
try/except at one call site; no new I/O loop, no new subprocess
**Constraints**: NFR-001 (zero net-new reds against the named baseline counts),
NFR-003 (shared test-venv lock contention is environmental, not attributable)
**Scale/Scope**: two functions touched (`_wp_blocks_step`, `_should_advance_wp_step`),
zero new exception classes (`MissionSelectorAmbiguous` already exists), `repo_root`/
`mission_slug` threaded through exactly one call site beyond `_should_advance_wp_step`'s
own signature (`_dn_dependency_gate`'s WP-iteration branch, `:1680`) — one source file
touched (`runtime_bridge.py`), not three

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after this design, and again after
the 2026-09-07 narrowing.*

- **Single canonical authority** (DIRECTIVE_044): FR-009's anchoring calls
  `mission_runtime.placement_seam(...).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)`
  directly, inline — the SAME primitive `_mission_routes_through_coordination` already
  calls at `runtime_bridge.py:265-275` for a different kind. No second anchoring
  mechanism is invented (the pre-narrowing draft's `resolve_primary_anchor_dir` helper is
  deleted along with Seam 1 — it existed only to be shared between the two seams, and
  Seam 1 no longer exists in this plan). PASS.
- **Architectural alignment** (DIRECTIVE_001): `mission_runtime.placement_seam` is
  already imported by `runtime_bridge.py` (twice: `:261`, `:1535`) — this mission adds no
  new inter-module dependency edge (`runtime.next` → `mission_runtime` is already a live,
  enforced-pair-compliant edge). PASS, confirmatory `tests/architectural/test_layer_rules.py`
  run is still worthwhile given a new import (`MissionSelectorAmbiguous`) enters
  `runtime_bridge.py`.
- **Tiered rigour / DDD**: `_should_advance_wp_step` is core guard-decision-feeding logic
  — held to the higher rigour tier: red-first tests per FR/AC, not just a smoke test.
- **ATDD-first**: satisfied by the red-first test plan below (C-008's four named
  reproductions), executed in the implement phase per DIRECTIVE_034/041.
- **Terminology canon** (C-007): this plan and its tasks/implementation use
  "Mission"; `feature_dir`/`feature-dir` remain as pre-existing code identifiers,
  not renamed.

No charter violation requires a Complexity Tracking entry — see that section below
(empty by design).

## Project Structure

### Documentation (this mission)

```
kitty-specs/runtime-advance-guard-topology-wp-completion-01M1W6VZ/
├── plan.md                        # This file
├── tracer-approach.md             # Seeded this phase, appended during implementation
├── tracer-design-decisions.md     # Seeded this phase, appended during implementation
├── tracer-tooling-friction.md     # Seeded this phase, appended during implementation
└── tasks.md / tasks/*.md          # Phase 2 output (/spec-kitty.tasks — NOT this phase)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are warranted:
this is a bug fix inside an existing, already-modeled runtime seam (no new data model,
no new contract surface, no external API). The "Key Entities" already stated in
spec.md (`MissionArtifactKind`, `WpEnding`, `Lane.UNINITIALIZED`) are sufficient
data-model documentation for a fix of this size.

### Source Code (repository root)

Single project, existing structure — no new top-level directories, and (post-narrowing)
exactly ONE source file touched:

```
src/runtime/next/
└── runtime_bridge.py               # FR-004/005: _wp_blocks_step's new
                                     #   `lane is Lane.UNINITIALIZED` disjunct
                                     # FR-009: _should_advance_wp_step gains
                                     #   repo_root/mission_slug params + inline
                                     #   placement_seam(...).read_dir(WORK_PACKAGE_TASK)
                                     #   anchoring; its one real production call site
                                     #   (_dn_dependency_gate's WP-iteration branch,
                                     #   :1680) threads them through
                                     # FR-010: that same call site gains a new
                                     #   except MissionSelectorAmbiguous arm,
                                     #   sibling to the existing
                                     #   except CanonicalStatusNotFoundError arm

tests/runtime/next/
├── test_coord_topology_fixture.py             # NEW — WP02-owned. Coord-topology fixture
│                                               #   builder (reusable, parameterized on the
│                                               #   coord side's seeded status events), the
│                                               #   feature_dir.name->mission_slug empirical
│                                               #   spike, and WP02's own FR-009-isolated
│                                               #   reproduction (an in_progress-claimed WP,
│                                               #   NOT an uninitialized one — see "Test
│                                               #   Strategy" below for why isolating FR-009
│                                               #   from FR-004 this way matters). Renamed
│                                               #   from the pre-narrowing draft's
│                                               #   test_coord_topology_fixture_repro1.py,
│                                               #   which also carried #3883-only content
│                                               #   that is deleted.
├── test_advance_guard_uninitialized_wp.py     # NEW — WP01-owned. FR-004/005 direct +
│                                               #   non-coord end-to-end reproduction.
└── test_advance_guard_coord_reachability.py   # NEW — WP01-owned. Imports WP02's fixture
                                                #   builder for the coord-topology
                                                #   end-to-end reproduction (FR-009, both
                                                #   fixes together) and the FR-010
                                                #   raise-and-catch reproduction. Renamed
                                                #   from the pre-narrowing draft's
                                                #   test_advance_guard_raise_and_catch.py,
                                                #   which also carried #3883-only content.
```

**`runtime_bridge_io.py` and `runtime_bridge_composition.py` are NOT touched by this
mission** (post-narrowing). Neither file is named by any surviving FR. See "Explicitly
not touched" below for the one specific line-level decision this narrowing had to make
explicit (whether `_check_composed_action_guard`'s own `_should_advance_wp_step` call in
`runtime_bridge_composition.py:557` also needs anchoring — it does not, proven, not
assumed).

**Structure Decision**: Single project, existing module layout. No new packages, no
new directories, one source file touched.

## The seam — `_wp_blocks_step` / `_should_advance_wp_step` (FR-004/005/009/010, #3884)

`src/runtime/next/runtime_bridge.py:781-810`. Current `implement` branch (`:799-807`):

```python
    if step_id == "implement":
        return (
            state.is_blocked
            or (state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED))
        )
```

**Root cause (verified against `src/specify_cli/status/wp_state.py`)**:
`UninitializedState` (registered at `_STATE_MAP["uninitialized"]`, `:673`) does not
override `is_blocked` (base class default `False`, `:85-86`) and its `lane`
(`Lane.UNINITIALIZED`, `:280-281`) is not in `is_run_affecting`'s active-lane set
(`{planned, claimed, in_progress, for_review, in_review, approved}`, `:100-109`) —
so `is_run_affecting` is also `False`. Both disjuncts evaluate `False`, and the
function returns `False` (does not block) purely because "never claimed" was never
enumerated anywhere in this branch, not because any code deliberately decided it is
safe.

**Fix (minimal, additive — one new disjunct, no restructuring):**

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

**Why this satisfies FR-005 (scoping) exactly, verified, not assumed:**

- The `is_acceptable_ending(...)` early-return (`:794-798`) runs BEFORE this branch
  and is untouched — `UNINITIALIZED` never satisfies it (`is_acceptable_ending`'s
  truth table only admits `approved`/`done`/provenance-`canceled`, confirmed in
  `src/specify_cli/status_lanes.py:33,42-56`), so approved/done/operator-canceled
  behavior for every OTHER lane is unaffected.
- The `review` branch (`:808-809`) is untouched — this is an `implement`-only fix.
- `_should_advance_wp_step`'s own no-`tasks/`-dir early return
  (`runtime_bridge.py:754-755`, `if not tasks_dir.is_dir(): return True`)
  **is touched by this plan (see "FR-009 — anchoring" below)** — but only to
  change WHICH directory `tasks_dir` is computed from (`anchor_dir` instead of raw
  `feature_dir`, only when the caller opts in), never the early-return logic
  itself. For the genuinely-no-`tasks/`-dir case (AC-3's `plan`-family example),
  the anchored `tasks_dir` still does not exist and the function still returns
  `True` — see the explicit no-op verification below.
- The `except ValueError` branch in `_should_advance_wp_step` is confirmed NOT to
  fire for `"uninitialized"` (`wp_state_for` returns `UninitializedState()` cleanly
  — `_STATE_MAP` has the key registered, `src/specify_cli/status/wp_state.py:671-698`)
  — matching AC-4. **The exact line range is `runtime_bridge.py:768-773`, not
  spec.md's `:763-767`** — see "Flagged Deviations" below (preserved verbatim from
  the pre-narrowing draft; the finding is unaffected by the narrowing).

### FR-009 — anchoring `_should_advance_wp_step` itself, inline (no shared helper)

**The gap, verified live.** `_should_advance_wp_step` (`runtime_bridge.py:738-780`)
does its own unanchored PRIMARY-partition read — `tasks_dir = feature_dir /
"tasks"` (`:753`) — before it ever reaches the per-WP loop that calls
`_wp_blocks_step` (where FR-004's `Lane.UNINITIALIZED` fix lives). For a real
COORD-topology mission, `tasks/` exists on the mission's primary checkout
(`WORK_PACKAGE_TASK` is a `_PRIMARY_ARTIFACT_KINDS` member, `src/mission_runtime/
artifacts.py:69,147-155,261`) but is invisible via the raw coord-worktree
`feature_dir` this function receives at its one genuinely load-bearing production
call site — `_dn_dependency_gate`'s WP-iteration branch, a *direct* call at
`:1680`, not routed through `_check_cli_guards`. So for that mission,
`tasks_dir.is_dir()` is `False` on the coord worktree even though `tasks/WP*.md`
exist on primary, `_should_advance_wp_step` hits its own early return and returns
`True` unconditionally, and the per-WP loop — the only place FR-004's new disjunct
can run — is never reached. FR-004's fix is therefore structurally inert for the
exact production scenario (#3884 on a COORD-topology mission) this mission exists
to fix, unless this same anchoring is also applied here.

**Design: call the existing primitive directly — no new shared helper.** The
pre-narrowing draft of this plan extracted a shared `resolve_primary_anchor_dir`
helper into `runtime_bridge_io.py` specifically so both `gather_artifact_presence`
(the former Seam 1) and `_should_advance_wp_step` could call the identical logic
without duplicating it (DIRECTIVE_044). With Seam 1 deleted, that shared-helper
rationale disappears — there is only ONE consumer left (`_should_advance_wp_step`
itself), so the anchoring is written inline, directly against the already-existing
`mission_runtime.placement_seam(...)` primitive `runtime_bridge.py` already imports
for an unrelated read at `:265-275`/`:1535` — the same primitive, not a new one, and
not routed through a helper that would now have exactly one caller:

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
        # WP-lane state is a STATUS_STATE-kind, coord-partition read; it stays on
        # feature_dir even after anchoring tasks_dir to primary (this mirrors the
        # pre-narrowing draft's own FR-002, which no longer exists as a separate
        # requirement now that Seam 1 is gone, but the invariant it named is still
        # true and still binding here).
```

**`mission_slug` fallback (`feature_dir.name`) — stated explicitly.** No production
call site needs the fallback: the one real caller (`_dn_dependency_gate`) already has
`ctx.mission_slug` in scope. The fallback exists for direct unit-test call sites that
supply `repo_root` but not `mission_slug`. Precedent for this exact fallback shape:
`_mission_slug_from_feature_dir` (`src/runtime/next/_internal_runtime/
retrospective_terminus.py:63-65`) already does `return feature_dir.name` as a
documented "best effort" mission-slug derivation elsewhere in this codebase.

**Gating on `repo_root is not None` (not a new separate flag) is deliberate**,
for the same three reasons the pre-narrowing draft established for Seam 1's
now-deleted `gather_artifact_presence` anchoring — restated here since they apply
identically to this one surviving call:

1. It reuses the #3704 precedent (`repo_root` already means "the caller has opted
   into primary-aware resolution") — no second toggle.
2. It is a true no-op for every existing test call site that omits `repo_root`
   (dozens of call sites across `tests/next/test_runtime_bridge_unit.py`,
   `tests/specify_cli/next/test_runtime_bridge.py`, and others, all calling
   `_should_advance_wp_step(step_id, feature_dir)` with exactly two positional
   arguments) — `anchor_dir` stays `feature_dir`, byte-identical to today.
3. It naturally satisfies the Edge Case "a `flattened`/`single_branch`-topology
   mission where `feature_dir` already IS the primary checkout... must be a
   no-op there" — `placement_seam(...).read_dir(WORK_PACKAGE_TASK)` for such a
   mission resolves to the SAME directory `feature_dir` already denotes (per
   `PlacementSeam.read_dir`'s own contract: "a PRIMARY-partition kind resolves the
   primary mission dir... for EVERY topology and coord state"), so `anchor_dir ==
   feature_dir` by construction. **This mission's own checkout (`single_branch`
   topology) is itself a live regression fixture for this no-op property.**

**Call-site threading — exactly one edit, verified as the only genuinely load-bearing
one.** `_should_advance_wp_step` has three theoretical call sites in the pre-narrowing
codebase: `_check_cli_guards:858`, `_check_composed_action_guard`
(`runtime_bridge_composition.py:557`), and `_dn_dependency_gate`'s WP-iteration
branch, direct call at `:1680`. This plan threads `repo_root`/`mission_slug` into
**only the third** — see "Explicitly not touched" below for the traced proof that the
other two do not need it.

```python
        try:
            should_advance = _should_advance_wp_step(
                current_step_id, feature_dir, repo_root=repo_root, mission_slug=mission_slug
            )
        except CanonicalStatusNotFoundError as exc:
            ...  # unchanged existing arm
```

`mission_slug`/`repo_root` are already local variables in this exact function
(`mission_slug = ctx.mission_slug` at `:1667`, `repo_root = ctx.repo_root` at
`:1670`, both bound before line 1680) — no new resolution needed, purely mechanical
threading at the one line already being edited to add the new `except` arm below.

### FR-010 — the one new catch site, and why it targets `MissionSelectorAmbiguous`,
not a new exception class

**Empirically verified during the 2026-09-07 narrowing work (not assumed, not
carried forward from the pre-narrowing draft's own untested assumption).** The
pre-narrowing draft assumed (for the now-deleted Seam 1, and by extension for this
surviving Seam 2 extension) that a corrupt/missing `meta.json` fixture would raise
some concrete exception when `placement_seam(...).read_dir(...)` tries to resolve a
PRIMARY-partition kind, and deferred identifying exactly which one to a WP-internal
empirical spike (mirroring `CoordWorktreeResolutionError`'s fail-loud precedent).
This narrowing work ran that spike directly against `WORK_PACKAGE_TASK` (the kind
FR-009 actually uses) instead of leaving it to the tasks phase, and found the
assumption **did not hold**:

```python
placement_seam(repo_root, "totally-bogus-mission-slug-zzz").read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)
# -> no raise. Returns <repo_root>/kitty-specs/totally-bogus-mission-slug-zzz, which .exists() is False.
```

Tracing why, against `resolve_artifact_surface`'s own docstring
(`src/mission_runtime/resolution.py:1976-2014`): "a PRIMARY-partition kind resolves
the primary mission dir... for EVERY topology and coord state (it never transits
coord)" — resolving a PRIMARY-partition kind's directory is pure path composition
off the canonicalized `mission_slug` (via `resolve_planning_read_dir`), never a
`meta.json` content read. `CoordinationBranchDeleted` (the exception the
pre-narrowing draft's Seam 1 spike found most concrete evidence for) can only fire
for a COORD-partition kind transiting the coord-state classifier — `WORK_PACKAGE_TASK`
never reaches that branch at all. The ONE exception `resolve_artifact_surface`'s own
docstring documents that a PRIMARY-partition kind CAN still raise is
`MissionSelectorAmbiguous` ("When `mission_slug` is an ambiguous handle, propagated
from handle canonicalization — no silent pick") — confirmed live: `mission_runtime/
resolution.py` itself locally imports `MissionSelectorAmbiguous` from
`specify_cli.missions._read_path_resolver` in five separate places for exactly this
purpose, an established, existing pattern this mission's own new import (into
`runtime_bridge.py`) simply follows.

**So FR-010 is narrower and simpler than the pre-narrowing draft's FR-006 ever was
for this call**: no new exception class, no "raise or otherwise surface" ambiguity to
resolve, and only ONE catch site (the one call-site edit FR-009 already makes) —
because the only failure mode this specific `read_dir(WORK_PACKAGE_TASK)` call can
actually produce is a genuinely ambiguous `mission_slug`, not a resolution-directory
existence problem (a nonexistent-but-unambiguous mission slug resolves to a real,
if absent, `Path`, which then correctly flows into the pre-existing
`tasks_dir.is_dir()` early return — that is FR-005's protected shape, not a new
failure mode).

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
        except MissionSelectorAmbiguous as exc:  # NEW — FR-010, sibling arm, same shape
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

`MissionSelectorAmbiguous` is imported at the top of `runtime_bridge.py` (a new,
module-level `from specify_cli.missions._read_path_resolver import
MissionSelectorAmbiguous`), matching how `CanonicalStatusNotFoundError` is already
imported there (`:181`).

### Explicitly not touched (scope boundary, proven, not merely stated)

- **`_check_cli_guards:858`'s own `_should_advance_wp_step` call.** Verified live
  control-flow trace: `_check_cli_guards` is called from exactly two sites, both
  inside `_dn_dependency_gate` — the WP-iteration branch (`:1729`) and the
  non-WP-iteration pre-check (`:1774`). The `:1729` call only executes AFTER the
  direct `_should_advance_wp_step` call at `:1680` (the one this plan anchors) has
  already returned `True` (else the function returns early at `:1698-1711` before
  ever reaching `:1729`). So `_check_cli_guards`'s own internal `_should_advance_wp_step`
  call at `:858` (gated to `step_id in ("implement", "review")`, which is exactly
  when the WP-iteration branch is active) is, for this exact step family, ALWAYS
  reached with the identical `feature_dir`/`repo_root`/`mission_slug` inputs the
  `:1680` call already resolved successfully moments earlier, with no filesystem
  mutation in between. Anchoring `:858`'s call too would be dead-weight
  duplication of a computation whose outcome is already known — not a functional
  requirement. **Left un-threaded deliberately, not by oversight.** (`:1774`'s
  non-WP-iteration pre-check never reaches `:858` at all — `step_id` there is, by
  construction, the complement of `_is_wp_iteration_step(...)`.)
- **`_check_composed_action_guard:557`'s own `_should_advance_wp_step` call**
  (`runtime_bridge_composition.py`). Verified live: composition dispatch
  (`_dn_composition_dispatch`) runs strictly AFTER `_dn_dependency_gate` in
  `decide_next_via_runtime`'s phase order (`runtime_bridge.py:2348`). For
  `implement`/`review` steps specifically, `_dn_dependency_gate`'s WP-iteration
  branch (`:1678-1756`) ALWAYS runs first and ALWAYS intercepts a
  `should_advance == False` verdict before composition dispatch is ever reached,
  for EVERY mission family (registered or not) whose current step is
  `implement`/`review` — this is unconditional on `_is_wp_iteration_step`, not
  scoped to `software-dev`. So `:557`'s own call, when it IS reached (only once
  `_dn_dependency_gate` already returned `None`, i.e. already agreed
  `should_advance == True` for the SAME `feature_dir`/`repo_root`/`mission_slug`
  triple with no intervening mutation), can never independently disagree with the
  already-established verdict. Anchoring it would touch a second file
  (`runtime_bridge_composition.py`) for zero behavioral benefit. **This mission
  therefore does not touch `runtime_bridge_composition.py` at all** — the one
  file this narrowing keeps out of scope beyond `runtime_bridge_io.py`. If a
  future caller ever invokes `_check_composed_action_guard` directly for
  `implement`/`review`, independent of `_dn_dependency_gate` (no such caller
  exists in `src/` today — grepped, confirmed), that call path would need this
  same anchoring; flagged here as a documented boundary, not silently dropped.
- **`gather_artifact_presence` / `runtime_bridge_io.py` entirely** — PR #3923's
  surface, not this mission's (spec.md C-009).

## Gate Set (charter Specify/Plan lens catalog, applied to THIS diff, post-narrowing)

| Gate | Applies? | Reason |
|------|----------|--------|
| `make lint` (ruff/mypy, advisory) | **Yes** | New code (new params, new branch, new except arm) must pass ruff/mypy strict with zero suppressions per CLAUDE.md Code Style |
| pytest shards (`tests/runtime`, `tests/runtime/next`, `tests/next`, `tests/specify_cli/next`, `tests/specify_cli/status`) | **Yes** | This mission's entire blast radius; NFR-001's named baseline is exactly these shards |
| `make test-fast` | **Yes** | Charter-mandated baseline for ordinary changes |
| Kernel coverage ≥90% | **No** | No `src/kernel/**` file is touched |
| Mission-loader coverage ≥90% | **No** | No `src/specify_cli/mission_loader/**` file is touched |
| commitlint | **Yes** | Universal PR-title/commit-message gate, not diff-specific |
| markdown lint | **Yes** | This mission edits `plan.md` + 3 tracer `.md` files (and `tasks.md`) |
| architecture/docs consistency (`tests/architectural/test_layer_rules.py`) | **Yes (confirmatory)** | A new import (`MissionSelectorAmbiguous`) enters `runtime_bridge.py`; the package-level `runtime.next → mission_runtime`/`specify_cli` edges already exist (no new edge), but re-running the layer-rule test is cheap given a new import lands in a module this gate watches |
| Doctrine schema freshness | **No** | No `src/doctrine/**` artifact touched |
| Contextive glossary | **No** | No new/renamed glossary-tracked term |
| TID251 banned-API | **Yes** | New import added (`MissionSelectorAmbiguous`); covered by ruff's TID251 rule as part of `make lint` |
| Typer JSON error surface | **No** | No Typer CLI command signature or `--json` error path is touched |
| `patch()` target validation | **Yes** | New tests will monkeypatch `_should_advance_wp_step` (module-level, at `runtime.next.runtime_bridge._should_advance_wp_step`, matching `tests/runtime/test_bridge_composition.py:962`'s and `tests/runtime/test_bridge_decide_next.py`'s established precedent for patching this exact name) |
| Bandit | **Yes** | Universal static-security gate on touched Python files; expected to pass trivially (no subprocess/eval/pickle/new I/O sink introduced) but run, not assumed |
| pip-audit | **No** | No dependency change |
| `uv.lock` freshness | **No** | No dependency change |
| SonarCloud Quality Gate | **Yes** | Universal PR gate; the charter's binding floor (`.kittify/charter/charter.md:262`, "pytest with 90%+ test coverage for new code") applies to every new line/branch this mission introduces |

"We'll run the tests" is not a gate statement — the pytest-shard row above is scoped
to the exact directories NFR-001 names, not a bare `pytest tests/`.

## Test Strategy (per FR/AC, red-first, DIRECTIVE_034/041)

### C-008's five named red-first reproductions (post-narrowing — the former
reproductions #1 and most of #2 were #3883-only and are deleted; #3 and #4 survive
and are joined by a new #0 that isolates FR-009 from FR-004; #2/former-#4 is
narrowed to FR-010's one actual catch site)

0. **WP02's own FR-009-isolated reproduction** (`test_coord_topology_fixture.py`;
   proves the coord-topology reachability bug BY ITSELF, deliberately NOT
   conflated with FR-004's separate, already-known `_wp_blocks_step` bug —
   design choice, stated explicitly: an uninitialized WP would ALSO make
   `_should_advance_wp_step` wrongly return `True` today for a reason that has
   nothing to do with coord-anchoring, namely `_wp_blocks_step`'s own pre-fix
   `Lane.UNINITIALIZED` gap, so it cannot isolate FR-009 alone). Fixture: primary
   checkout dir with a real `tasks/WP01-*.md`; a separate coordination-worktree-
   shaped `feature_dir` holding only `status.events.jsonl`, seeded with a claim +
   `in_progress` transition for that WP id — a lane that ALREADY correctly blocks
   under today's un-patched `_wp_blocks_step` (`is_run_affecting=True`, not in
   `{FOR_REVIEW, APPROVED}`, so it returns `True`/blocks without needing FR-004's
   disjunct at all). Call `_should_advance_wp_step("implement", coord_feature_dir)`
   — the function's CURRENT, plain 2-arg signature, no anchoring keywords, callable
   against genuinely unmodified code — and assert it (wrongly) returns `True`
   (permits advancement) even though the WP is actively `in_progress`: RED,
   because the unanchored `tasks_dir` read hits its own no-`tasks/`-dir early
   return on the coord worktree and never reaches the per-WP loop at all, so
   `_wp_blocks_step` — which would correctly say "block" for `in_progress` even
   today — is never even consulted. Paired with a regression pin: the SAME call
   against `primary_dir` directly (`_should_advance_wp_step("implement", primary_dir)`,
   no coord split) already correctly returns `False` (blocks) today, confirming
   the bug is specifically the coord-anchoring gap, not `_wp_blocks_step`'s own
   logic. This reproduction is genuinely callable and RED against **unmodified**
   production code (no new signature needed) — WP02 remains independent test-only
   work with no dependency on WP01, mirroring the pre-narrowing draft's own
   "test-only, no dependency" framing for this WP.
1. **Direct + non-coord end-to-end reproduction** (`test_advance_guard_uninitialized_wp.py`;
   FR-004/005, SC-003; written against the function's CURRENT, plain 2-arg
   `_should_advance_wp_step` signature — no directory I/O, no `placement_seam`, no
   coord-topology fixture): a WP file under `tasks/` with zero events. Direct
   `_wp_blocks_step("implement", UninitializedState(), has_provenance=False)` call
   — assert `True` (post-fix) vs. `False` (pre-fix, the RED assertion). Also assert
   `_should_advance_wp_step("implement", feature_dir)` returns `False` for the
   mission as a whole (AC-2), using a **non-coord fixture whose `feature_dir`
   directly contains `tasks/`** (no `repo_root`/`mission_slug` keywords — the
   pre-FR-009 2-arg call), and separately assert AC-3/AC-4's **UN-anchored** case
   only (no-`tasks/`-dir early return still returns `True` for this same 2-arg
   call; `except ValueError` confirmed not to fire for `"uninitialized"`) as
   explicit regression pins.
2. **Coord-topology end-to-end reproduction** (`test_advance_guard_coord_reachability.py`,
   importing WP02's fixture builder; FR-004+FR-009 TOGETHER, AC-5, SC-007 — proves
   FR-004's fix genuinely fires for the production scenario, not just at the
   `_wp_blocks_step` unit level, and not only in isolation as reproduction #0
   proved FR-009 alone; necessary red-first sequencing: written and confirmed red
   as soon as `_should_advance_wp_step`'s extended signature exists, BEFORE the
   anchoring body is applied, then confirmed green after):
   - Fixture: reuse WP02's builder with an UNINITIALIZED-WP variant (zero coord-side
     status events for the WP, the builder's default) — the SAME fixture shape as
     reproduction #0, seeded differently.
   - As soon as the signature extension lands (parameters accepted, anchoring body
     not yet applied): call `_should_advance_wp_step("implement", coord_feature_dir,
     repo_root=<repo_root>, mission_slug=<slug>)` and assert it (wrongly) returns
     `True` — RED, because the early return still fires on the unanchored
     `tasks_dir` computation regardless of whether the `Lane.UNINITIALIZED`
     disjunct has landed.
   - Once the anchoring body change lands: confirm the SAME call now returns
     `False` — GREEN, proving BOTH the `Lane.UNINITIALIZED` disjunct AND the
     anchoring extension are in place together.
   - Also assert the parallel primary-dir call (`_should_advance_wp_step("implement",
     primary_dir)`, no anchoring needed since it's already the primary checkout)
     returns the same `False` — confirming the coord-anchored answer agrees with
     the already-correct primary-direct answer.
3. **FR-010 raise-and-catch reproduction** (`test_advance_guard_coord_reachability.py`;
   SC-008; written red-first as soon as the extended signature and the new
   `except MissionSelectorAmbiguous` import exist): a fixture where `mission_slug`
   is genuinely ambiguous (two or more mission directories under `kitty-specs/`
   sharing a common prefix that the supplied `mission_slug` value matches
   non-uniquely, so `placement_seam(repo_root,
   mission_slug).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)` raises
   `MissionSelectorAmbiguous` for real, not via a monkeypatch). Call
   `rb._dn_dependency_gate(ctx)` directly (constructing `DecideNextContext` by hand,
   `current_step_id="implement"`, matching `tests/runtime/next/
   test_cli_guard_family.py:487`'s established construction pattern for this kind
   of test) and assert a `DecisionKind.blocked` Decision carrying the exception's
   message — RED (uncaught exception) before the new `except` arm lands, GREEN
   after.
4. **No-op regression pins** (`test_advance_guard_coord_reachability.py`; Edge
   Cases, AC-3/AC-5's negative space): (a) call `_should_advance_wp_step` with
   `repo_root` set for THIS mission's own `single_branch`-topology checkout and
   assert the return value is unchanged from the un-anchored 2-arg call; (b) a
   parallel assertion for the legitimate no-`tasks/`-dir case (a
   `plan`-family-shaped fixture) with `repo_root` set, asserting it still returns
   `True`.

### 90%+ new-code coverage arithmetic (charter.md:262), stated explicitly

This mission's new lines fall into three enumerable groups, each with a named
direct test: (1) the one new `lane is Lane.UNINITIALIZED` disjunct in
`_wp_blocks_step` — reproduction #1 (direct call); (2) `_should_advance_wp_step`'s
new `repo_root`/`mission_slug` parameters and inline anchoring call (both the
anchoring-SUCCEEDS path and the no-op paths) — reproductions #0/#2 plus the no-op
pins (#4); (3) the new `except MissionSelectorAmbiguous` arm at
`_dn_dependency_gate:1680` — reproduction #3, with real failure injection (a
genuinely ambiguous fixture), not a monkeypatched exception. Every group has at
least one named direct test.

## Baseline (NFR-001)

Cite verbatim, not re-derived: `tests/runtime tests/next tests/specify_cli/next
tests/specify_cli/status` (fast/unit tier) — **1666 passed, 1 skipped, 325
deselected**. `tests/runtime/next tests/next` (full) — **598 passed**. The exact
invocation `pytest tests/runtime --ignore=tests/runtime/next` — **672 passed, 1
skipped** (673 collected; the naive `pytest tests/runtime -q` WITHOUT `--ignore`
collects 746 / 745 passed — a different, larger number that reads as a false
regression to an implementer who runs the bare command, per NFR-001's own explicit
warning).

**How the mission's own runs distinguish pre-existing red from introduced red**: run
these exact invocations FIRST, before any production-code change (WP02, alongside
its own red-first tests), and record the counts. Any count that already differs
from NFR-001's stated baseline at that point is either (a) this repo's standing
`red-main-release-discipline` — named pre-existing P0 reds (#2736, #2772, #1834 per
CLAUDE.md) — or (b) an environmental/stale-venv false-red per the baseline-red
gotcha (auth, `SPEC_KITTY_SYNC_*` opt-outs, stale install, stale venv) — classify
per that gotcha's four categories before touching anything; never fold a
pre-existing red into this mission's own accounting (Standing Order #9). Only a
count that is red on this branch AND green on `main`/`upstream/main` at the same
commit is this mission's to fix. Re-run the SAME three invocations after WP01 and
confirm the counts match NFR-001/SC-005 exactly (zero net-new reds), classifying
any new red the same way before assuming it is this mission's fault.

## Campsite-clean scope (charter Standing Order #2)

**No campsite-clean opening step applies to this mission.** Both touched functions
were read in full during this plan phase:

- `_wp_blocks_step` (~30 lines) gets exactly one new `or`-disjunct in an existing
  `return` expression — no structural change.
- `_should_advance_wp_step` (~45 lines post-fix) gains two new keyword-only
  parameters and a ~6-line conditional anchoring block, inline against an
  already-imported primitive — it does not push the function toward the
  complexity ceiling (15) or introduce new nesting depth.
- `_dn_dependency_gate`'s WP-iteration branch gains one new `except` arm, sibling
  to an existing one of the same shape.

This is stated explicitly per Standing Order #2 rather than silently skipped — no
Sonar-flagged god-surface is being touched, so there is nothing to campsite-clean
ahead of the functional change.

## Tracer files

Seeded at the original (pre-narrowing) plan phase (`tracer-approach.md`,
`tracer-design-decisions.md`, `tracer-tooling-friction.md`), matching the naming
convention already used across this repo's other missions. Each carries a short
seed entry plus this narrowing's own dated append; implementation appends further,
it does not replace.

## Phasing — ONE PR (spec-kitty default)

**This diff qualifies as reviewable-in-one-sitting** — even more so post-narrowing
than the original two-issue draft: one source file (`runtime_bridge.py`), two
functions, one new `except` arm, zero new exception classes.

**Work packages, matching the mission's actual `wps.yaml`/`tasks.md` shape (WP02 →
WP01 → WP03) — not the pre-narrowing draft's hypothetical WP1a/WP1b/WP2/WP3
naming, which this section now retires in favor of the real WP ids:**

- **WP02 (first, independent, test-only, `dependencies: []`)**: build the
  reusable coord-topology test fixture (primary dir with a real `tasks/WP*.md`,
  plus a separate coordination-worktree-shaped `feature_dir` holding only
  `status.events.jsonl`, parameterized on which lane-transition events to seed on
  the coord side), resolve the `feature_dir.name`→`mission_slug` empirical
  question, and write Test Strategy item 0 — the FR-009-isolated reproduction,
  using an `in_progress`-claimed WP specifically so the reproduction does not
  conflate FR-009's coord-anchoring bug with FR-004's separate, already-known
  `_wp_blocks_step` bug — against **unmodified** production code (genuinely
  callable today, no new signature required, since the reproduction uses the
  function's current plain 2-arg call). **This WP's own coord fixture survives
  the narrowing and remains genuinely needed**: the
  reachability bug (FR-009) is coord-specific by definition — it only manifests
  when `feature_dir` is a coordination worktree lacking `tasks/` while primary has
  it — so a coord-topology fixture is not optional scaffolding, it is the one
  fixture shape that can demonstrate the bug at all. What changed is WHICH guard
  the fixture proves: the former WP02 proved #3883's `tasks.md`-presence guard
  failure; the narrowed WP02 proves #3884's `_should_advance_wp_step` reachability
  failure — same fixture shape, different assertion, because the underlying
  primary-vs-coord-worktree split that makes the fixture necessary is identical
  for both bugs (both are consequences of `tasks/`/`spec.md`/`tasks.md` being
  PRIMARY-partition artifacts a coord worktree never receives).
- **WP01 (`dependencies: [WP02]`)**: the `_wp_blocks_step` `Lane.UNINITIALIZED`
  disjunct (FR-004/005) + `_should_advance_wp_step`'s FR-009 anchoring extension +
  FR-010's one new catch arm, plus reproductions #1, #2 (its RED-then-GREEN
  assertions), #3, and the no-op pins (Test Strategy items 1, 2, 3, 4) — reusing
  WP02's coord-topology fixture rather than rebuilding an equivalent one.
- **WP03 (`dependencies: [WP01]`, last)**: NFR-001 baseline re-verification +
  final tracer-file updates + the PR description's rollout-impact operator note.

**Chokepoints.** No CI-gate, migration-chain, or runtime-state-schema
serialization point applies to this mission's WPs — there is no schema migration,
no multi-stage CI gate ordering, and no shared runtime-state file any WP writes
that another WP also writes. The one shared resource in this mission's blast
radius is the test-venv lock (#3283, NFR-003): avoid scheduling more than one WP's
`pytest` invocation to run concurrently in separate lanes where avoidable, and any
lock-contention timeout observed during concurrent WP execution must be classified
per the baseline-red gotcha (environmental), never folded into this mission's own
pass/fail accounting.

## Reflexivity — rollout impact (spec.md's Edge Cases note)

Per spec.md's Edge Cases: before this fix, `_should_advance_wp_step` was never
anchored with `repo_root` on a coord-topology mission, so its `tasks/` lookup
against the coordination worktree always failed and the function returned
`True` unconditionally on `implement` — skipping the per-WP loop entirely,
regardless of whether any WP was in-progress, blocked, or rejected, not only
never-claimed. Shipping this fix will newly (and correctly) block ANY
coord-topology mission currently in `implement` with a WP that is not in an
acceptable/handed-off state — a WP that was never claimed (#3884), but equally
one that is merely `in_progress`, `blocked`, or rejected without operator
provenance — including, now that FR-009 ships alongside FR-004, a real
COORD-topology mission in that state, not only a SINGLE_BRANCH/LANES one. This
is an **operational note for the PR description and merge hand-off, not a new
code requirement**: the implement/review phase should recommend (in the PR
body, not as a new FR) that whoever merges this spot-checks EVERY
currently-in-`implement` coord-topology mission (not only ones already
suspected to have a never-claimed WP) immediately after merge, so an operator
is not surprised by a mission newly blocking on its next `next` call with no
user-visible change of their own. No mission-tracking code change is proposed
for this — it is a call-out, matching the spec's own framing of it as a real
operational discontinuity, not an internal test-suite delta. (The #3883 half
of this note — the query/advance disagreement unblocking a mission — belongs
to PR #3923's own rollout, not this mission's; not repeated here.)

## Complexity Tracking

*Empty — no Charter Check violation requires justification. The surviving fix is
additive, minimal-diff, to an existing, already-modeled seam; no new project, no
new pattern beyond the already-proven #3704 `repo_root`-threading shape.*

## Flagged Deviations — a citation found to be wrong during this plan's own
verification pass (per instructions: state explicitly, do not quietly correct
without flagging)

spec.md's User Story 2, Acceptance Scenario 4, cites: "the pre-existing `except
ValueError` branch in `_should_advance_wp_step` (`runtime_bridge.py:763-767`,
'Unknown lane … treat as not-yet-handed-off')". **Verified against the live file**:
lines 763-767 are actually `for wp_file in wp_files:` / `wp_match = re.match(...)`
/ `wp_id = wp_match.group(1)...` / `ending = committed_authority.wp_ending(...)` —
the setup of the per-WP loop, not the except branch. The actual `try`/`except
ValueError` block (with the "Unknown lane … treat as not-yet-handed-off" comment)
is at **`runtime_bridge.py:768-773`** (`try:` at `:768`, `except ValueError:` at
`:770`, the two-line comment at `:771-772`, `return False` at `:773`). This is a
genuine additional citation drift beyond the three rounds already recorded in
spec.md's own revision history — it does not change any FR/AC/Constraint's
*substance* (the described behavior — that this branch does not fire for
`"uninitialized"` — is correct, only the line-number pointer is off by 5-7 lines),
and it does not change this plan's fix design. Recorded here rather than silently
corrected, per this mission's own review culture (`reviews/spec-*.yaml` documents
multiple prior rounds of exactly this class of finding). The implement/tasks phase
should use `runtime_bridge.py:768-773`, not `:763-767`, when citing this branch.

No other spec.md citation checked during this plan phase (an exhaustive line-by-line
sweep of every FR/AC/Constraint/NFR/SC citation, not a sample) was found to be
wrong.

### Second round — confirmed adversarial-review findings against this plan
itself (`reviews/plan.confirmed.yaml`), addressed and recorded here

- **PLAN-FIT-002 / PLAN-FIT-003 (citation drift, this plan's own prose, not
  carried from spec.md)**: two of this plan's own new citations
  (`runtime_bridge_composition.py:672-682` for the FR-006 broad-catch
  precedent, and `wp_state.py:672` for `_STATE_MAP["uninitialized"]`) were
  found wrong against the live checkout — corrected in place above to
  `:646-663` and `:673` respectively. Neither changes the fix's substance;
  both are pointer corrections. This plan's earlier claim that "all line
  citations below were re-verified" (top of this document) did not, in fact,
  hold for these two plan-original citations — recorded here rather than
  silently fixed, matching this mission's own stated review culture.
- **PLAN-FIT-001 (severity 4 — scope completion, not a citation fix)**: this
  plan's first draft implemented FR-004/005 entirely inside `_wp_blocks_step`
  without noticing that `_should_advance_wp_step` — the function that must
  reach `_wp_blocks_step`'s per-WP loop in the first place — did its own
  unanchored `tasks_dir = feature_dir / "tasks"` read and returned `True`
  unconditionally for a COORD-topology mission before ever reaching that
  loop, making FR-004's fix structurally inert for the actual #3884
  production scenario. This plan now extends FR-001's anchoring mechanism
  (via one shared, extracted helper — not a duplicated copy, per
  DIRECTIVE_044) to `_should_advance_wp_step` itself — see "Seam 2
  extension" above for the full design, its explicit no-op verification
  against FR-005's protected legitimate no-`tasks/`-dir case, the two
  additional FR-006 catch-site arms this requires, and the new coord-topology
  end-to-end reproduction (#4) that proves FR-004 genuinely fires post-fix.
  This is recorded as a plan-level completion of FR-004/005's own stated
  intent (spec.md's Rollout-impact text already claims this correctness),
  not a new spec requirement — the "Seam 2 extension" section states the
  scope-framing reasoning explicitly.
- **PLAN-SEQ-001/002/003 and PLAN-VERIFY-001/002**: addressed by splitting
  WP1 into WP1a/WP1b (Phasing section), adding the explicit "Write scopes /
  Lane coordination" and "Chokepoints" notes (Phasing section), pinning
  Test Strategy item 1 (reproduction #1)'s Call (b) exact construction method, and citing
  charter.md's binding 90%+ coverage floor with an explicit new-lines-vs-tests
  accounting (Gate Set / Test Strategy) — see those sections for the
  applied fixes; not repeated here.

### Third round — confirmed adversarial-review findings against this plan
itself (`reviews/plan-round2.confirmed.yaml`), addressed and recorded here

- **PLAN-SEQ-001 (severity 3, unresolved after round 1's fix)**: round 1's
  WP1a/WP1b split still had reproductions #3 and #4 calling
  `_should_advance_wp_step(..., repo_root=..., mission_slug=...)` — a
  keyword interface that does not exist on the function's live/pre-fix
  signature (`def _should_advance_wp_step(step_id, feature_dir)`) until
  WP2's Seam 2 extension lands; calling it that way pre-fix would raise
  `TypeError`, not return `True` as the plan asserted for the RED state
  (and reproduction #2 had the identical defect one level up, via
  `gather_artifact_presence`'s new `mission_slug` parameter and the
  not-yet-existing `PrimaryPlacementResolutionError`). **Fixed by
  re-deriving what each reproduction genuinely needs**: reproduction #3
  (WP1a) now tests the `Lane.UNINITIALIZED` fix and `_should_advance_wp_step`
  end-to-end using ONLY the function's current 2-arg signature against a
  non-coord fixture (`feature_dir` directly contains `tasks/`) — sidestepping
  the anchoring question entirely, since WP1a's own fix needs no anchoring to
  be tested. Reproductions #2 and #4 — which inherently need WP2's new
  signature/exception surface to be callable at all — move from WP1b into
  WP2 itself, written red-first at WP-internal commit granularity (test
  immediately after the new signature/exception lands, before the
  anchoring/catch-site body change; green immediately after). The "anchored"
  half of AC-3/AC-4's no-op pin (previously folded into reproduction #3) also
  moves to WP2's "Additional narrow unit tests," where the extended
  signature it needs already lives. See the Test Strategy section's
  reproductions #2/#3/#4 and the Phasing section's WP1a/WP1b/WP2 bullets for
  the full corrected text.
- **PLAN-FRESH-001 (severity 4)**: the 2 NEW FR-006 catch-site arms
  PLAN-FIT-001's Seam 2 extension added (`_check_composed_action_guard`'s own
  `_should_advance_wp_step` call, `_dn_dependency_gate`'s WP-iteration-branch
  direct call) had zero red-first failure-injection coverage — reproduction
  #2 still said "three FR-006 call sites" (stale, pre-extension wording) and
  reproduction #4 (credited by the coverage-arithmetic section for these two
  arms) only ever exercises the anchoring-SUCCEEDS happy path, never injects
  a resolution failure. **Fixed**: reproduction #2 now drives a corrupt/
  missing-`meta.json` fixture through all FIVE real FR-006 catch sites — its
  new reproduction #2 Calls (c)/(d) specifically target the two PLAN-FIT-001 arms, asserting
  a non-empty failure list from `_check_composed_action_guard` (c) and a
  `DecisionKind.blocked` Decision from a direct `_dn_dependency_gate` call on
  the WP-iteration branch (d). Reproduction #2's prose now says "all FIVE
  real FR-006 catch sites" (verified count: the original 3 + PLAN-FIT-001's
  2 = 5; unaffected by the PLAN-SEQ-001 resequencing above, which only moves
  *when* reproductions are written, not how many catch sites exist). The
  coverage-arithmetic section's six groups collapse to five, with all 5
  catch-site arms now attributed to reproduction #2 instead of splitting
  attribution between reproduction #2 (3 arms) and reproduction #4 (2 arms,
  incorrectly, since #4 injects no failure).
- **PLAN-FRESH-002 (severity 3)**: `gather_artifact_presence`'s `anchor_dir`
  block was shown twice — inline in the Design decision section (Seam 1),
  and again as the extracted `resolve_primary_anchor_dir` helper in the Seam
  2 extension section — never reconciled, risking an implementer keeping
  BOTH (the exact "second anchoring mechanism duplicated" outcome
  DIRECTIVE_044 forbids). **Fixed by moving the helper's one definition
  earlier**: Seam 1's Design decision section now defines
  `resolve_primary_anchor_dir` once, from the start, and shows
  `gather_artifact_presence`'s own post-extraction body (a one-line call to
  the helper) immediately after — the only body ever shown for that
  function. The Seam 2 extension section no longer re-derives the helper;
  it states explicitly that `_should_advance_wp_step` calls the SAME
  already-defined helper and shows only its own call site.

### Fourth round — confirmed adversarial-review findings against this plan
itself (`reviews/plan-round3.confirmed.yaml`), addressed and recorded here

- **PLAN-FRESH2-001 (severity 4)**: round 2's fix for PLAN-FRESH-001 added
  Calls (c)/(d) for the two PLAN-FIT-001 catch sites but, in doing so, left
  the THIRD original FR-006 catch site — `_check_composed_action_guard`'s
  own wrap of its own `gather_artifact_presence` call
  (`runtime_bridge_composition.py:543-549`, distinct from the `:557`
  `_should_advance_wp_step` reproduction #2 Call (c)/(d) target) — with zero
  failure-injection coverage: reproduction #2's Call (a) only exercises the raise directly
  (not through `_check_composed_action_guard`), and reproduction #2's Call (b) only reaches
  the two `_dn_dependency_gate`/`_check_cli_guards` wraps. Both the
  per-reproduction summary sentence and the coverage-arithmetic section
  still wrongly credited "all 5 catch sites" to reproduction #2's Calls (a)-(d). **Fixed**:
  added reproduction #2's Call (e) — same corrupt/missing-`meta.json` fixture as (a), calling
  `_check_composed_action_guard(action, coord_feature_dir,
  mission="software-dev", repo_root=<repo_root>)` directly and asserting a
  non-empty failure list. Verified live that this catch site fires
  unconditionally (the `gather_artifact_presence` call at `:543-549` sits
  before the `action in ("implement", "review")` gate at `:550`), unlike the
  `:557` site reproduction #2's Call (c)/(d) target — so `action` may be any value for (e), stated
  explicitly to contrast with (c)'s hard requirement (see PLAN-FRESH2-002
  below). The summary sentence and coverage-arithmetic section now attribute
  the original 3 catch sites to reproduction #2's Calls (b) and (e) specifically (not a
  blanket "(a)-(d)"), with (a) recorded as confirming the underlying raise
  rather than exercising a catch site.
- **PLAN-FRESH2-002 (severity 3)**: reproduction #2's Call (c) never pinned `action` to
  `"implement"`/`"review"`, the only values for which the `:557`
  `_should_advance_wp_step` call is even reached (verified live,
  `runtime_bridge_composition.py:550`) — an implementer following
  reproduction #1's Call (a)'s `action="tasks"` precedent could write reproduction #2's Call (c)
  with an `action` that never reaches the catch site under test, making the
  assertion pass vacuously. **Fixed**: reproduction #2's Call (c) now states explicitly that
  `action` must be `"implement"` or `"review"`, with the one-line reason
  (any other value returns before line `:557`).
- **PLAN-FRESH2-003 (severity 2)**: the WP2 red-first commit-ordering worked
  example named only reproduction #2's Call (a)'s and Calls (c)/(d)'s commit placement, leaving
  reproduction #2's Call (b) — which depends on the `_dn_dependency_gate` catch-arm commit for
  its GREEN state, a different commit surface than Call (a)'s
  exception/helper addition or Calls (c)/(d)'s `_should_advance_wp_step`
  signature extension — to guesswork. **Fixed**: the worked example now
  places every reproduction #2 Call explicitly, per-Call rather than as one undifferentiated
  "reproduction #2" blob: Call (a)/(e) at the exception+param-addition
  commit (green once the raise/catch-arm for each respectively lands); Call
  (b) red at that SAME early commit (needs only `_check_cli_guards` to
  propagate the raise — true today, no new catch arm required for RED),
  green only after the separate `_dn_dependency_gate` catch-arm commit; and
  Calls (c)/(d) plus reproduction #4 only once `_should_advance_wp_step`'s
  extended signature lands, green after their own respective catch-arm/
  anchoring-body commits. **PLAN-FRESH3-001 (fifth round, below) further
  split reproduction #2's Call (b) into two independently-fixtured halves,
  (b-i)/(b-ii) — see the Test Strategy and WP2 Phasing sections above for
  the corrected per-half commit placement, which supersedes this bullet's
  "Call (b) red/green as one unit" simplification.** **PLAN-FRESH4-002
  (sixth round, below) further merged Calls (c)/(d) into ONE test with two
  sequential assertions, sharing one fixture, because they share fate — see
  the Test Strategy and WP2 Phasing sections above for the corrected
  commit-placement framing (the merged test stays red until BOTH catch-arm
  commits land, not independently green per Call), which supersedes this
  bullet's "Calls (c)/(d)... their own respective catch-arm... commits"
  framing above.**

### Fifth round — confirmed adversarial-review findings against this plan
itself (`reviews/plan-fresh-3.yaml`), addressed and recorded here

- **PLAN-FRESH3-001 (severity 4)**: reproduction #2's Call (b) described
  itself as a single fixture reaching BOTH `_check_cli_guards` wraps
  (`:1729` WP-iteration, `:1774` non-WP-iteration), but for the WP-iteration
  half this is false, verified by tracing the live control flow precisely:
  `_dn_dependency_gate`'s WP-iteration branch calls
  `_should_advance_wp_step(current_step_id, feature_dir, repo_root=repo_root,
  mission_slug=mission_slug)` directly at `:1680` — through the Seam 2
  extension's SAME `resolve_primary_anchor_dir` helper, with the SAME
  `feature_dir`/`repo_root`/`mission_slug` triple — BEFORE `_check_cli_guards`
  is ever reached at `:1729`. With no filesystem mutation between the two
  calls, a uniform corrupt/missing-`meta.json` fixture (the one Call (a)/(b)
  originally described) fails both calls identically, so the `:1680` call
  always raises FIRST and is caught by its own new sibling arm (added by the
  Seam 2 extension's own catch-site-extension item 3) — `_check_cli_guards`
  at `:1729`, and its except arm (FR-006's original catch site #1), is never
  reached at all under that fixture. This also means that arm is
  structurally subsumed by `:1680`'s arm for any REAL production
  primary-resolution failure on this branch, not merely untestable as
  fixtured — the two calls always share fate outside of an artificial mock.
  **Resolved as "genuinely reachable with a distinguishing fixture", not
  "structurally unreachable/dead code"**: isolating one
  `resolve_primary_anchor_dir`-reaching call from a sibling call sharing the
  identical inputs requires an asymmetric mock, not a real fixture — no real
  filesystem state can make a pure, deterministic function succeed for one
  caller and fail for another given byte-identical arguments. (This
  document's round-4 draft had asserted, at this point, that reproduction
  #2's Calls (c)/(d) already established this technique as precedent — that
  citation was false: (c)/(d)'s own Test Strategy text said only "a
  fixture," never "mock," and was itself never fixed to state a real
  mechanism. PLAN-FRESH4-002, sixth review round, corrected (c)/(d)
  directly; see the Test Strategy reproduction #2 entry above. No precedent
  is claimed here.) **Fixed** — Call (b) is now split into two
  explicit sub-fixtures, (b-i) (non-WP-iteration branch, `:1774`, reusing the
  uniform fixture — verified live to have no competing earlier call, since
  `_check_cli_guards`'s own `:858` `_should_advance_wp_step` call is gated to
  `step_id in ("implement", "review")` and this branch's `step_id` is by
  construction the complement) and (b-ii) (WP-iteration branch, `:1729`,
  patching `_should_advance_wp_step` to return `True` unconditionally so the
  `:1680` call never raises, while the SAME real corrupt fixture still fails
  `gather_artifact_presence`'s own `:851` call inside `_check_cli_guards`) —
  see the Test Strategy reproduction #2 entry, the "Together... cover the
  three catch sites" summary sentence, the coverage-arithmetic section, and
  the WP2 Phasing commit-ordering bullet, all updated consistently so no
  sibling section retains the stale single-fixture framing. The code at
  `:1729` remains correct to write (belt-and-suspenders symmetry with
  `:1774`'s independently-live arm, and protection against a future
  reordering of the two calls); "5 real catch sites" stands, each
  independently test-exercised, with (b-ii)'s fixture now stated explicitly
  as the asymmetric one it must be.
- **PLAN-FRESH3-002 (severity 2)**: reproduction #1's Calls (a)/(b) and
  reproduction #2's Calls (a)-(e) shared bare letters throughout the
  document — round 3's own Call (e) addition grew the collision surface from
  4 to 7 same-lettered-different-meaning Calls without adding a
  reproduction-number qualifier anywhere, including the WP2 commit-ordering
  section, which said bare "Call (a)/(e)" and "Calls (c)/(d)" relying
  entirely on surrounding prose (itself sometimes several lines removed) to
  disambiguate from reproduction #1's own (a)/(b). **Fixed**: the
  first/defining occurrence of each Call in every section is now prefixed
  with its owning reproduction number — "reproduction #1's Call (a)" vs.
  "reproduction #2's Call (b)" — including reproduction #1's own Call (a)/(b)
  definitions (so later bare references have an unambiguous antecedent to
  point back to), the WP2 Phasing commit-ordering bullets, the
  coverage-arithmetic section, and the round-history bullets above that
  quote specific Calls out of their defining paragraph. **This is not every
  individual bare reference in the document (PLAN-FRESH4-003, sixth review
  round: the prior wording here overclaimed "grepped exhaustively... every...
  reference")** — later within-paragraph continuation references still rely
  on an antecedent established earlier in the same paragraph, which was
  verified not to create real ambiguity, not re-verified by grep here.

### Sixth round — plan-phase ruling (`reviews/plan.ruling.md`), applied here
after the plan phase HALTed under the review protocol's oscillation rule
(severity>=3 findings went 3 -> 2 -> 1 -> 2 across four rounds against
`reviews/plan-fresh-4.yaml`). Per the ruling, this round is a targeted fix of
the three survivors — a class-level share-fate audit for PLAN-FRESH4-002, not
a re-derivation of the fix design, which the ruling reconfirms as settled.

- **PLAN-FRESH4-001 (severity 3)**: the Gate Set's `patch() target
  validation` row never listed `_should_advance_wp_step`, even though round
  4's own (b-ii) design requires patching exactly that name at module level.
  **Fixed**: added to the Gate Set row above, with the fully-qualified patch
  target (`runtime.next.runtime_bridge._should_advance_wp_step`) pinned
  against the same precedent (b-ii)'s Test Strategy text already cites.
- **PLAN-FRESH4-002 (severity 4)**: two separate defects, fixed differently.
  (1) Round 4 had asserted that reproduction #2's Calls (c)/(d) already
  established "an asymmetric mock" as precedent for (b-ii)'s own new mock —
  (c)/(d)'s own text never said "mock," only "fixture," so the citation was
  fabricated. **Fixed by deletion**: the false citation is removed from the
  Fifth-round PLAN-FRESH3-001 entry above; no precedent is claimed there any
  more. (2) The finding's underlying claim was structurally correct: (c) and
  (d) both resolve through the identical pure `resolve_primary_anchor_dir`
  helper with byte-identical arguments and no mutation between them, so no
  real fixture can differentiate them — they share fate, exactly the defect
  class round 4 fixed for reproduction #2's Call (b) (split into (b-i)/
  (b-ii)), but left unfixed for this second instance. **Fixed by writing**:
  the Test Strategy's (c)/(d) entry above is now ONE test, not two,
  explicitly stating the share-fate property and pinning the actual
  mechanism (a module-level patch on `_should_advance_wp_step`, the same
  monkeypatch technique (b-ii) uses, direction inverted — raise instead of
  return `True` — while `gather_artifact_presence`'s own separate call is
  left genuinely real against a valid fixture). The summary sentence and the
  coverage-arithmetic section are updated to match (one test driving two
  catch-arm assertions, not two independently-fixtured Calls). Checking
  every other call pair in the plan for the same share-fate property found
  no further unfixed instance: reproduction #1's Call (a)/(b) pair is
  deliberately dual-path (both are SUPPOSED to produce the same result, per
  C-003 — sharing fate is the assertion there, not a defect); reproduction
  #2's (a)/(b-i)/(e) all reuse the same uniform corrupt-fixture condition to
  exercise genuinely different, independent catch arms (not to differentiate
  two calls from each other), which is not the share-fate problem.
- **PLAN-FRESH4-003 (severity 1)**: PLAN-FRESH3-002's own remediation text
  overclaimed "grepped exhaustively... every... reference," which a literal
  grep for `Call (` still contradicts (over a dozen bare within-paragraph
  continuation references remain, none creating real ambiguity). **Fixed**:
  the overclaim is deleted and the PLAN-FRESH3-002 entry above now states
  what was actually done — the first/defining occurrence per section, not
  every individual reference — without re-grepping to manufacture
  exhaustiveness that was never required.

**Not in scope for this fix round, per the ruling**: the `CLAUDE.md` drift
(it instructs reading `SPEC-KITTY-LEDGER.md`, which does not exist in this
repository — that ledger lives in the operator's workspace) is real and
correctly flagged by the adversarial rounds above, but it is a repository
documentation defect, not this mission's work. Left flagged, not fixed.

## Narrowing — scope reduction to #3884 only (operator ruling, 2026-09-07)

This section is appended after the plan phase's own preserved review history above
(rounds 2 through 6, `reviews/plan.confirmed.yaml` through `reviews/plan.ruling.md`)
rather than rewriting it, per this mission's own established review culture of
recording a correction explicitly instead of silently editing history. Everything
above this section describes the plan as it stood through the sixth review round,
on the two-issue (#3883+#3884) premise those rounds reviewed. What follows records
what changed and why, verified against the live checkout and the live GitHub API on
2026-09-07, not assumed.

### What was removed, and why

**The entire former "Seam 1" section** (`gather_artifact_presence`'s topology
anchoring — FR-001/002/003/006/007/008, the `resolve_primary_anchor_dir` helper,
the new `PrimaryPlacementResolutionError` exception class, the 8-row
`mission_slug` call-site threading table, the five FR-006 catch sites across
`runtime_bridge.py`/`runtime_bridge_composition.py`/`runtime_bridge_io.py`, and
reproductions #1 and #2 of the former Test Strategy) is deleted. Verified reason:
draft PR **#3923** (`codex/upgrade-preview-mission-health`, base `main`) already
implements the equivalent fix — independently, via a different, further-progressed
mechanism (`_artifact_presence_read_dir` / `kind_for_mission_file` / `placement_seam`)
in the exact file (`runtime_bridge_io.py`) Seam 1 would have edited. Confirmed via
the paginated GitHub API (not the truncated-at-100 `gh pr view --json files`): PR
#3923 has 125 changed files, touches `runtime_bridge_io.py`, and its diff mentions
`gather_artifact_presence` 9 times. This is not a finding that Seam 1's own design
was wrong — four review rounds (`reviews/plan-fresh-3.yaml`,
`reviews/plan-fresh-4.yaml`, `reviews/plan.ruling.md`) had already converged it to a
sound, if elaborate, fix. It is redundant with a more-progressed, independently
authored fix for the same bug, landing in the same file. Shipping both would either
conflict at merge time or duplicate the single-canonical-authority the charter
already requires (DIRECTIVE_044) — so this mission cedes the territory rather than
racing or reconciling two designs for the same seam.

**NFR-002** (the "any new diagnostic is additive-only" non-functional requirement)
is removed — it existed solely to bound a hypothetical new field on
`ArtifactPresenceSnapshot` that Seam 1's own FR-006 might have needed; the surviving
fix touches no dataclass and adds no field.

**C-001 through C-005** (the `gather_artifact_presence`-scoping constraints: no
whole-function primary anchoring, `guard_failures` byte-exactness across a dozen
named test files, the dual-guard-path requirement for the `"tasks"` step, and the
two "explicitly out of scope" constraints bounding a fuller kind-aware migration)
are removed — all five exist only to scope or protect Seam 1's own blast radius,
which no longer exists in this mission.

### What survives, and why

**FR-004/FR-005 survive verbatim** — the `_wp_blocks_step` `Lane.UNINITIALIZED`
disjunct and its scoping constraint were always independently #3884's, sharing no
implementation seam with #3883 (spec.md's own pre-narrowing User Story 2 already
said as much explicitly, and this narrowing does not have to argue the point — it
was already established).

**The former "Seam 2 extension" (PLAN-FIT-001) survives, promoted from an implicit
plan-level completion to explicit spec.md requirements (FR-009/FR-010).** This is
the one piece of the narrowing that needed real technical re-derivation, not just
deletion, because — as PLAN-FIT-001 itself established in round 2
(`reviews/plan.confirmed.yaml`, preserved in "Second round" above) —
`_should_advance_wp_step` has its own SEPARATE, unanchored `tasks_dir` read in
`runtime_bridge.py`, independent of `gather_artifact_presence`'s read in
`runtime_bridge_io.py`. Losing Seam 1 does not remove this second read or the bug
it causes; `runtime_bridge.py` is not a file PR #3923 touches (verified: zero
mentions of `_wp_blocks_step`, `_should_advance_wp_step`, or `UninitializedState`
in its diff), so fixing this read remains entirely this mission's job.

What changed in HOW it survives, versus the pre-narrowing draft:

1. **No shared helper.** The pre-narrowing draft extracted `resolve_primary_anchor_dir`
   into `runtime_bridge_io.py` specifically so Seam 1 and Seam 2 could share one
   anchoring-and-translation function (DIRECTIVE_044 — never two copies). With Seam
   1 gone, there is exactly one caller left; the anchoring is now written inline in
   `_should_advance_wp_step` itself, against the SAME already-existing
   `mission_runtime.placement_seam(...)` primitive `runtime_bridge.py` already
   imports for an unrelated read — not a new helper with one caller, and not a
   second copy of anything (see "The seam" section's FR-009 subsection above).
2. **No new exception class, and a narrower catch-site scope.** The pre-narrowing
   draft invented `PrimaryPlacementResolutionError` and wired FIVE catch sites
   across three files, deferring to an implement-phase spike which of several
   candidate exceptions a corrupt/missing `meta.json` fixture would actually raise.
   This narrowing ran that spike directly, now, against the actual kind FR-009
   uses (`MissionArtifactKind.WORK_PACKAGE_TASK`, not `PRIMARY_METADATA`), and
   found the assumption did not hold: a corrupt/missing `meta.json` does not raise
   at all for a PRIMARY-partition kind (resolution is pure path composition, never
   a `meta.json` content read); the one exception that CAN fire is the
   already-existing `MissionSelectorAmbiguous`. Combined with the "explicitly not
   touched" proof (above) that `_check_cli_guards:858` and
   `_check_composed_action_guard:557`'s own calls are provably inert duplicates of
   the one real call site, this narrows FR-006's five-catch-site design down to
   ONE catch site (`_dn_dependency_gate:1680`) catching ONE already-existing
   exception type. See "FR-010" above for the full empirical trace.
3. **The reachability requirement is now an explicit spec.md FR (FR-009/FR-010),
   not an implicit "plan-level completion of FR-004/005's own stated intent."**
   The pre-narrowing draft's own "Seam 2 extension" section argued this was within
   spec intent without needing a new spec.md requirement, because spec.md's
   Rollout-impact edge case already implied coord-topology applicability. With
   Seam 1's own FR numbering gone, and this mission now standing entirely on
   #3884, the operator's narrowing instruction asked this to be named plainly in
   spec.md rather than left as an inference from an edge-case sentence — done, as
   FR-009/FR-010.

### The coord-topology fixture (`wps.yaml`'s WP02) — kept, repurposed, justified
not assumed

WP02's coord-topology fixture (a primary checkout holding real `tasks/WP*.md`, plus
a separate coordination-worktree-shaped `feature_dir` holding none of it) was
originally built to reproduce #3883's `tasks.md`-presence guard failure. It is
**kept**, because the SAME fixture shape is exactly what FR-009's reachability bug
needs to reproduce: the bug only manifests when `feature_dir` is a coordination
worktree lacking `tasks/` while primary genuinely has it — a coord fixture is not
incidental scaffolding here, it is the one shape that can demonstrate the bug at
all. Reused, not rebuilt: the underlying primary-vs-coord split is the same
structural fact (`tasks/`/`spec.md`/`tasks.md` are all `_PRIMARY_ARTIFACT_KINDS`
members a coord worktree never receives) that made the fixture necessary for
either bug. What changed is the fixture's OWNING repository file and the assertion
built on top of it — see `tasks/WP02-coord-topology-fixture-repro1.md`'s successor
prompt for the as-narrowed content.

### Not carried forward as a new finding — the two WP02 empirical spikes' outcome

The pre-narrowing draft's WP02 also carried two empirical spikes: (a) whether
`feature_dir.name` reliably yields the `mission_slug` `placement_seam` expects, and
(b) which exception a corrupt/missing `meta.json` read raises. Spike (a)'s question
is still live for FR-009's own fallback (`mission_slug` defaulting to
`feature_dir.name`) and is carried forward into the narrowed WP02/WP01. Spike (b)'s
question is now answered directly in this section (FR-010's empirical trace) rather
than left to a WP-internal spike — the answer (`MissionSelectorAmbiguous`, not a new
exception class) is now load-bearing design, not an open item.
