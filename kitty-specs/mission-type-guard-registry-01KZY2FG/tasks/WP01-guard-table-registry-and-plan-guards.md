---
work_package_id: WP01
title: Guard-table registry, strict/tolerant split, and plan's guard table
dependencies: []
requirement_refs:
- C-001
- C-002
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Guard dispatch registry + strict/tolerant split
history:
- at: '2026-08-13T22:40:00Z'
  actor: system
  action: Prompt generated during hand-authored /spec-kitty.tasks dispatch (no LLM tasks-phase command available in this run; canonical task-prompt-template.md structure followed directly).
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge_cores.py
- src/runtime/next/runtime_bridge_composition.py
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_io.py
- tests/runtime/test_bridge_cores.py
- tests/runtime/test_bridge_composition.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Guard-table registry, strict/tolerant split, and plan's guard table

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the
rest of this prompt. If a different profile fits better for your harness, run
`spec-kitty agent profile list` and justify the substitution in the Activity Log.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: (fill in at claim time)

---

## Objectives & Success Criteria

Close the guard-evaluation fall-through defect (issue #3386) across both call paths, and give
`plan`-type missions their own guard table:

1. Replace `evaluate_guards`'s `if research / if documentation / else software-dev` chain
   (`src/runtime/next/runtime_bridge_cores.py:351-374`) with an explicit `_GUARD_TABLES`
   registry (FR-001, FR-006).
2. Split the single shared `_cores.evaluate_guards(snapshot)` call into a **strict lookup**
   (`evaluate_guards_strict`, raises `UnregisteredMissionFamilyError` for an unregistered
   family) that `_check_cli_guards` (`runtime_bridge.py:680-698`) calls **directly**, and a
   **tolerant wrapper** (catches that exception, logs at WARNING, returns `[]`) that
   `_check_composed_action_guard` (`runtime_bridge_composition.py:427-486`) calls **directly**
   (FR-003, FR-004, FR-005, C-001, C-002).
3. Author `_evaluate_plan_guards` (FR-002) and register it under `"plan"` in `_GUARD_TABLES`.
4. Add `"research.md"` to `runtime_bridge_io.py`'s `_PRESENCE_FILE_TAGS` so `plan`'s new
   `research`-step check can actually see the artifact.

**Done when**: T001/T002's RED tests are GREEN, `tests/runtime/test_bridge_cores.py` and
`tests/runtime/test_bridge_composition.py` pass **unmodified** in every pre-existing assertion
(SC-004 — zero assertion-value edits to existing tests), the 784-test baseline (see below) shows
zero new reds, and `mypy --strict` / `ruff check` (complexity ≤15, NFR-003) are clean on every
touched/added function.

## Context & Constraints

- **Binding source documents**: `.kittify/charter/charter.md` (ATDD-first C-011, Sonar
  Expectations complexity ceiling), `kitty-specs/mission-type-guard-registry-01KZY2FG/spec.md`
  (User Stories 1-3, FR-001–FR-006/FR-010/FR-011, NFR-001–NFR-003, C-001/C-002),
  `kitty-specs/mission-type-guard-registry-01KZY2FG/plan.md` §Seam & Module Placement (exact
  design), §ATDD-First Sequencing, §Baseline & Reflexivity, §Gate Set.
- **Do not touch**: anything in spec.md's Out of Scope list (the doctrine-override hatch, the
  two divergent meta readers, the dashboard default, the wider census, any `validate_meta`
  roster check, DRG guard modeling). If your diff would touch any of these files, STOP — you
  have drifted outside this WP's scope.
- **Line citations below were re-verified against the current checkout this session** (not
  carried over from plan.md unchecked) — `git log --oneline
  7deadff0a4f3dfd2744b5e1e35680c0d70f4565e..HEAD -- src/runtime/next/` is empty, confirming no
  drift since plan.md's own baseline capture. If your own checkout shows different line numbers
  when you start, re-verify by reading the file, not by trusting this prompt blindly — say so
  in the Activity Log if you find drift.
- **Zero new imports required** anywhere in this WP: `Callable` is already imported in
  `runtime_bridge_cores.py:73`; `_cores` is already imported in `runtime_bridge.py:162` and
  `runtime_bridge_composition.py:88`; `logger` already exists in
  `runtime_bridge_composition.py:101`.
- **`runtime_bridge_cores.py` is a zero-dependency pure leaf** (its own module docstring: "may
  import stdlib, `Lane`/decision types, and nothing else... every function here is pure: no
  filesystem, no git, no `meta.json` reads"). Do **not** add a logging call inside this module —
  the WARNING log belongs in `runtime_bridge_composition.py` only (see T005).

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-mission-type-guard-registry-01KZY2FG`. Completed changes must merge back into
  it.
- **Planning base branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG`
- **Merge target branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG`

> Prepare the workspace with `spec-kitty implement WP01` — it resolves the lane worktree from
> `lanes.json`; do not reconstruct the path by hand.

## ATDD Commit Sequence (charter C-011, binding — do not reorder)

This WP's commits, in order, mirror plan.md's ATDD-First Sequencing exactly, with the
PLAN-VERIFY-002 fix already applied (the RED commit asserts the **target/fixed shape directly**,
not "today's buggy output" — do not resurrect that rejected pattern):

1. **Commit 1 (RED)** — T001. Committed BEFORE any implementation commit.
2. **Commit 2 (RED)** — T002. Committed BEFORE any implementation commit, after Commit 1.
3. **Commit 3 (implementation)** — T003, T004, T005, T006 land together as one coherent commit
   (plan.md's own Campsite-Clean Scope / ATDD-Sequencing determination: these four concerns are
   one small, indivisible change, not artificially split by a tidy-up pre-commit). T001 and T002
   both flip to GREEN in this commit.
4. **Commit 4 (verification, optional as a separate commit)** — T007's checks; fold into Commit
   3 if your workflow prefers a single implementation commit, as long as the verification
   evidence lands in the Activity Log either way.

The reviewer will verify RED on this WP's base commit and GREEN on its final commit for every
assertion added in T001/T002 — do not let Commit 1/2 pass at the base commit for the wrong
reason (e.g. a typo in the assertion that happens to also fail).

## Subtasks & Detailed Guidance

### T001 — RED: FR-010 ATDD pin (`plan`/`review` target-shape) + User Story 2 AC3 (`plan`/`research` tightening)

- **Purpose**: Pin the mission's core, live defect (issue #3386's title) as a genuinely failing
  test before any fix lands, and pin the second, smaller behavior change plan.md's own
  Baseline & Reflexivity section flags (`plan`'s `research` step goes from "always passes,
  checks nothing" to "checks `research.md`").
- **Steps**:
  1. In `tests/runtime/test_bridge_cores.py`, add a test using the file's existing `_snapshot(...)`
     helper (defined at line ~190; reuse it, do not duplicate it) with
     `mission_family="plan", step_id="review"`. Assert
     `cores.evaluate_guards(_snapshot(mission_family="plan", step_id="review")) == []`.
     **Confirm this is genuinely RED before writing anything else**: run
     `.venv/bin/python -m pytest tests/runtime/test_bridge_cores.py -k plan_review -q` against
     the WP's base commit and observe it fail with the actual current output —
     `["Not all work packages are approved or done"]` — not a false-red from a typo.
  2. In the same file, add a test for `mission_family="plan", step_id="research"` covering both
     branches: `research.md` absent → `["Required artifact missing: research.md"]`;
     `research.md` present (`present_artifacts=frozenset({"research.md"})`) → `[]`. **Both
     assertions must be RED today**: `evaluate_guards` currently returns `[]` unconditionally
     for this snapshot (falls through to `_evaluate_software_dev_guards`'s bare `return []`
     default, since `"research"` is not one of software-dev's own step ids) — so the
     absent-artifact assertion is the one that proves RED (today it wrongly returns `[]` instead
     of the missing-artifact message).
  3. Do **not** add a companion "assert today's actual output" pin — the target-shape assertion
     alone is sufficient proof of the flip (this is the exact PLAN-VERIFY-002 fix: no
     passing-at-base assertion is committed as part of a "RED" commit).
- **Files**: `tests/runtime/test_bridge_cores.py`.
- **Validation**: both new tests fail at the WP's base commit for the stated reason; both pass
  once T003 lands.

### T002 — RED: FR-011 ATDD pin (unregistered-family fall-through, 3 assertions)

- **Purpose**: Pin the previously-uncovered fall-through itself — zero tests exist today (per
  spec.md FR-011's own grep-verified claim) that feed an unregistered `mission_family` to either
  call path.
- **Steps**:
  1. **Strict lookup raises** — in `tests/runtime/test_bridge_cores.py`, add a test calling
     `cores.evaluate_guards_strict(_snapshot(mission_family="totally-unregistered-family",
     step_id="review"))` inside `pytest.raises(cores.UnregisteredMissionFamilyError)`. RED today
     because neither the function nor the exception class exists yet (`AttributeError` — a
     genuine failure for the right reason).
  2. **`_check_cli_guards` propagates via an injection seam** — `_check_cli_guards` hardcodes
     `mission_family="software-dev"` (line 692), so no real caller can reach this state today
     (User Story 3's own framing: "defensive correctness... currently unreachable"). Use
     `monkeypatch` to make `rb._io_seam.gather_artifact_presence` return an
     `ArtifactPresenceSnapshot` with `mission_family="totally-unregistered-family"` regardless of
     the arguments `_check_cli_guards` passes it, then call
     `rb._check_cli_guards("review", tmp_path)` inside `pytest.raises(cores.UnregisteredMissionFamilyError)`
     (or via `cores.UnregisteredMissionFamilyError` imported as needed) and assert the exception
     propagates **out of `_check_cli_guards` itself** — this is the part of User Story 3
     Acceptance Scenario 3 that closes the "isolated, unwired helper" loophole; do not settle
     for only testing the strict function in isolation. RED today: `_check_cli_guards` ends with
     `return _cores.evaluate_guards(snapshot)` (the *tolerant* function), which currently exists
     but returns the software-dev misfire (or `[]`), never raises.
  3. **Composed path returns `[]` + WARNING log** — in `tests/runtime/test_bridge_composition.py`,
     call `_check_composed_action_guard("review", tmp_path,
     mission="totally-unregistered-family")` directly (the `mission` keyword param already
     exists) with `caplog.at_level(logging.WARNING)`. Assert the return value is `[]` (not the
     software-dev WP-iteration message) AND that a WARNING-or-above log record was captured
     naming `"totally-unregistered-family"`. **RED today for two independent reasons**: (a)
     `mission="totally-unregistered-family"` at `step_id="review"` today falls through to
     `_evaluate_software_dev_guards` → `_evaluate_wp_iteration_guard("review", ...)`, which
     returns the WP-iteration message for an empty/unapproved WP set — not `[]`; (b) no WARNING
     log call for this case exists anywhere in the module yet, so the `caplog` assertion fails
     regardless of (a).
- **Files**: `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_composition.py`.
- **Validation**: all three assertions fail at the WP's base commit for the stated reasons; all
  three pass once T003/T005/T006 land.

### T003 — `_GUARD_TABLES`, `UnregisteredMissionFamilyError`, `evaluate_guards_strict`, tolerant wrapper, `_evaluate_plan_guards`

- **Purpose**: The registry itself (FR-001, FR-006), the strict/tolerant split's shared
  foundation (FR-003–FR-005), and `plan`'s own guard table (FR-002) — all in
  `runtime_bridge_cores.py`.
- **Steps**:
  1. Add `_GUARD_TABLES: dict[str, Callable[[_ArtifactPresenceSnapshotLike], list[str]]]`
     mapping `"research"` → `_evaluate_research_guards`, `"documentation"` →
     `_evaluate_documentation_guards`, `"software-dev"` → `_evaluate_software_dev_guards`,
     `"plan"` → `_evaluate_plan_guards` (added in step 4 below).
  2. Add `class UnregisteredMissionFamilyError(ValueError):` — a new, local exception. Its
     docstring MUST include the cross-reference plan.md's Seam & Module Placement section
     specifies verbatim (this closes PLAN-ARCH-002, a confirmed plan-review finding already
     designed-in): a one-line note naming the sibling concept
     `charter.mission_type_profiles.UnknownMissionTypeError` — same shape (`ValueError`
     carrying the offending string), different layer (runtime guard-family dispatch vs. charter
     mission-type resolution); intentionally not unified. Do **not** import `charter` into this
     module to write that comment — it is prose only.
  3. Add `def evaluate_guards_strict(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:` —
     looks up `_GUARD_TABLES.get(snapshot.mission_family)`; calls it if found; raises
     `UnregisteredMissionFamilyError(snapshot.mission_family)` if not.
  4. Add `def _evaluate_plan_guards(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:` — a
     5-way `if`/`elif` on `snapshot.step_id`: `"specify"` → `_check_artifact_present(snapshot,
     SPEC_ARTIFACT)`; `"research"` → `_check_artifact_present(snapshot, "research.md")` (a new
     one-off literal — do not add a module constant for it; this module's own header comment at
     lines 79-91 already documents the "local literal duplicates" convention for exactly this
     case); `"plan"` → `_check_artifact_present(snapshot, PLAN_ARTIFACT)`; `"review"` → `[]`,
     with a comment citing the direct analogy to `_evaluate_documentation_guards`'s `accept`
     case at lines 455-456 ("terminal status commit step; publish gate is sufficient"); else →
     `[f"No guard registered for plan action: {action}"]` (fail-closed, matching the
     research/documentation families' own unknown-action convention). Register it under
     `"plan"` in `_GUARD_TABLES` from step 1.
  5. Change `evaluate_guards(snapshot) -> list[str]` (keep the name and signature
     byte-identical — existing direct callers, including
     `tests/runtime/test_bridge_cores.py`, keep working unmodified per SC-004) to:
     `try: return evaluate_guards_strict(snapshot) except UnregisteredMissionFamilyError:
     return []`. Add a one-line docstring note (this closes PLAN-VERIFY-005, a confirmed
     plan-review finding already designed-in): kept tolerant/public only for existing direct
     test callers; any **new** production call site should use `evaluate_guards_strict` instead
     so an unregistered family is never silently swallowed.
- **Files**: `src/runtime/next/runtime_bridge_cores.py`.
- **Validation**: T001's `plan`/`review` and `plan`/`research` assertions and T002's strict-raise
  assertion all go GREEN. `ruff check` complexity ≤15 on every new/changed function (NFR-003 —
  `_evaluate_plan_guards`'s 5-way flat chain is far under the ceiling).

### T004 — `_PRESENCE_FILE_TAGS`: add `"research.md"`

- **Purpose**: Without this, `_evaluate_plan_guards`'s `research` branch would always report
  `research.md` missing even when it exists on disk — a fresh silent-misbehavior defect inside
  this very fix (found during plan-authoring verification, not named by spec.md — see plan.md's
  tracer-design-decisions.md entry 5).
- **Steps**: Add `"research.md"` to the 9-tuple `_PRESENCE_FILE_TAGS` in
  `runtime_bridge_io.py` (lines 708-718 currently), making it a 10-tuple. Update the nearby
  module docstring claim ("mirrors the exact set of ... reads ... across all three mission
  families") to say "all four" once `plan` is registered.
- **Files**: `src/runtime/next/runtime_bridge_io.py`.
- **Validation**: T001's `research.md`-present branch (`[]` when `research.md` is in
  `present_artifacts`) goes GREEN. Confirm no existing per-family evaluator function reads the
  `"research.md"` tag (grep for the literal string in `runtime_bridge_cores.py` — it must appear
  nowhere except your new T003 code), so this addition is provably additive and does not affect
  NFR-001's zero-behavior-change guarantee for the three already-registered families.
- **Parallel?**: Yes, alongside T005/T006 (disjoint files).

### T005 — Composed path: strict call + WARNING-logging catch

- **Purpose**: FR-003, FR-004, C-001 — the composed path never raises for an unregistered
  family; it degrades to `[]` and logs at WARNING naming the family.
- **Steps**: In `_check_composed_action_guard` (`runtime_bridge_composition.py:427-486`), change
  the current last line, `return _cores.evaluate_guards(snapshot)` (line 486), to:
  ```python
  try:
      return _cores.evaluate_guards_strict(snapshot)
  except _cores.UnregisteredMissionFamilyError:
      logger.warning(
          "Unregistered mission_family %r reached the composed guard path; "
          "returning a neutral (empty) guard result.",
          mission,
      )
      return []
  ```
  (adapt exact message text to your judgment; the family value MUST appear in the log record, at
  WARNING level or above, per FR-004). `logger` already exists at module line 101; `_cores` is
  already imported at line 88 — no new imports.
- **Files**: `src/runtime/next/runtime_bridge_composition.py`.
- **Validation**: T002's composed-path assertion (returns `[]` + WARNING log captured) goes
  GREEN. Confirm `runtime_bridge.py:878-891`'s thin compat delegate (which forwards to this
  function) needs no change — do not add a duplicate log call there.
- **Parallel?**: Yes, alongside T004/T006 (disjoint files).

### T006 — Legacy path: direct strict call, no catch

- **Purpose**: FR-005, C-002, User Story 3 — the legacy/CLI-native path raises loudly, never
  silently degrades, for an unregistered family, and `_check_cli_guards` itself is the direct
  caller (not an isolated unwired helper).
- **Steps**: In `_check_cli_guards` (`runtime_bridge.py:680-698`), change the last line,
  `return _cores.evaluate_guards(snapshot)` (line 698), to `return
  _cores.evaluate_guards_strict(snapshot)`. **No try/except** — letting
  `UnregisteredMissionFamilyError` propagate uncaught IS the "raise loudly" requirement. `_cores`
  is already imported at line 162 — no new imports.
- **Files**: `src/runtime/next/runtime_bridge.py`.
- **Validation**: T002's `_check_cli_guards`-propagation assertion goes GREEN. Confirm via
  `grep -n "_check_cli_guards(" src/` that no existing caller passes anything other than the
  hardcoded `mission_family="software-dev"` — this raise path stays unreachable by any real
  caller today (defensive correctness only), which is the expected, documented state.
- **Parallel?**: Yes, alongside T004/T005 (disjoint files).

### T007 — Verify: GREEN, zero new reds, diff-coverage check

- **Purpose**: Close out the WP with the evidence the reviewer needs, per charter C-005 /
  plan.md's Gate Set.
- **Steps**:
  1. Run `.venv/bin/python -m pytest tests/runtime/test_bridge_cores.py
     tests/runtime/test_bridge_composition.py -q` — confirm all pass, including T001/T002's
     tests now GREEN, and confirm **zero** existing assertion had to change value (SC-004).
  2. Run `.venv/bin/python -m pytest tests/next/ tests/specify_cli/next/
     tests/integration/test_custom_mission_runtime_walk.py -q` — confirm zero new reds against
     the 784-passed/0-failed baseline (`7deadff0a4f3dfd2744b5e1e35680c0d70f4565e`). If a red
     appears that is not attributable to this WP's diff, classify it per CLAUDE.md's
     baseline-red gotcha (pre-existing #3284 / CI-environment / stale-install) before treating it
     as yours to fix.
  3. Run `mypy --strict` and `ruff check` on the four touched production files; both must be
     clean, zero suppressions added.
  4. Verify the diff-coverage critical-path gate (chokepoint — see tasks.md's Chokepoints
     section) locally: `uv run diff-cover --compare-branch=<merge-target-branch>
     --fail-under=90 --include 'src/runtime/next/*'` (adapt the exact invocation to whatever
     coverage report your local run produces via `--cov=src/runtime/next`). Record the result in
     the Activity Log.
- **Files**: none (verification only).
- **Validation**: all four checks pass; results recorded in the Activity Log with actual
  command output (not "looks fixed").

## Test Strategy

- **Targeted surface only** (charter C-005 / plan.md Gate Set): `tests/runtime/test_bridge_cores.py`,
  `tests/runtime/test_bridge_composition.py` (primary, this WP's own tests), plus
  `tests/next/`, `tests/specify_cli/next/`, `tests/integration/test_custom_mission_runtime_walk.py`
  (regression surface — NFR-001/NFR-002). Do **not** run the full `pytest tests/` suite.
- **Baseline**: 784 passed / 0 failed at `7deadff0a4f3dfd2744b5e1e35680c0d70f4565e` (cited, not
  re-run from scratch — re-run only the same four commands to compare).
- **Revert discipline**: every behavior change in this WP (registry dispatch, the strict/tolerant
  split, `plan`'s guard table, the `research.md` presence tag) has a test added in T001/T002 that
  fails if that specific change is reverted — this is a stated acceptance requirement for this
  WP, not an aspiration.

## Risks & Mitigations

- **NFR-001 regression risk**: the registry refactor must not change output for `software-dev`
  / `research` / `documentation` / typeless. Mitigation: T007's baseline re-run is the concrete
  check — `test_bridge_cores.py` and `test_bridge_composition.py` must pass **unmodified**
  (SC-004), not just "green."
- **NFR-002 regression risk**: the ≥24-test / ≥4-test custom-mission-type composed-path
  tolerance must stay green, unmodified. This WP only changes what happens for a family with NO
  `_GUARD_TABLES` entry — it must not touch `_should_dispatch_via_composition` or the
  agent-profile/contract-ref widening path those tests exercise. Do not edit any file outside
  this WP's `owned_files` list.
- **Silent loophole risk (User Story 3's own explicit warning)**: a unit-tested-but-unwired
  strict-raising helper would satisfy a literal test assertion while `_check_cli_guards`'s real
  call chain keeps delegating to the tolerant path. T002's injection-seam assertion against
  `_check_cli_guards` itself (not just `evaluate_guards_strict` in isolation) exists specifically
  to close this loophole — do not skip or weaken it.

## Review Guidance

- Confirm RED→GREEN on this WP's own base→final commit for every T001/T002 assertion (C-011).
- Confirm the `UnregisteredMissionFamilyError` docstring carries the cross-reference comment
  (PLAN-ARCH-002) and `evaluate_guards`'s docstring carries the tolerant-wrapper guidance note
  (PLAN-VERIFY-005) — both are one-line additions the plan already designed in; their absence is
  a real (if small) finding, not nitpicking.
- Confirm `_check_composed_action_guard` and `_check_cli_guards` are the **direct** callers of
  `evaluate_guards_strict` (grep the diff, don't just read the test names).
- Confirm no file outside `owned_files` was touched.

## Activity Log

> **CRITICAL**: entries MUST be in chronological order (oldest first, newest last). Append at
> the end.

- 2026-08-13T22:40:00Z – system – Prompt created.
