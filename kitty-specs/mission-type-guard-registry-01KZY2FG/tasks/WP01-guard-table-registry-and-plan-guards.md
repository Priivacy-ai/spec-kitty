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
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-type-guard-registry-01KZY2FG
base_commit: d12a98f81a1d5c6cc7df0319d016740f876fb3a0
created_at: '2026-08-14T00:07:27.793135+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Guard dispatch registry + strict/tolerant split
shell_pid: '695823'
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
- tests/runtime/test_bridge_io.py
role: implementer
tags: []
task_type: implement
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
   family) that `_check_cli_guards` (`runtime_bridge.py:785-803`, re-verified
   post-#3346-rebase — shifted +105 lines from 680-698, same code) calls **directly**, and a
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

### T001 — RED: FR-010 ATDD pin (`plan`/`review` target-shape) + User Story 2 AC2/AC3 (`specify`/`research` branches) + hardening for `_evaluate_plan_guards`'s `plan`-step and fail-closed-else branches (beyond spec.md's literal Acceptance Scenarios) + revert-discipline pin for the `research.md` presence tag

- **Purpose**: Pin the mission's core, live defect (issue #3386's title) as a genuinely failing
  test before any fix lands; pin `_evaluate_plan_guards`'s full 5-way branch set
  (`specify`/`research`/`plan`/`review`/fail-closed-else — the `specify`/`research`/`review`
  branches map to User Story 2's Acceptance Scenarios 2/3/1 respectively, while the `plan`-step
  and fail-closed-else branches are hardening coverage beyond what spec.md's Acceptance Scenarios
  literally mandate), not only the two branches (`review`, `research`) that happen to differ from
  today's fallthrough output; and give the `research.md` presence-tag fix (T004) real, disk-backed
  test coverage so reverting it is detectable (Test Strategy's "Revert discipline" bullet, below).
  **Every RED claim below was empirically re-run against this session's checkout, not reasoned
  from prose alone** — this WP was itself the subject of a confirmed review finding
  (TASKS-VERIFY-001) showing prose reasoning about RED status can be wrong; do not repeat that
  mistake when implementing.
- **Steps**:
  1. In `tests/runtime/test_bridge_cores.py`, add a test using the file's existing `_snapshot(...)`
     helper (defined at line ~190; reuse it, do not duplicate it) with
     `mission_family="plan", step_id="review"`. Assert
     `cores.evaluate_guards(_snapshot(mission_family="plan", step_id="review")) == []`.
     **Confirm this is genuinely RED before writing anything else**: run
     `.venv/bin/python -m pytest tests/runtime/test_bridge_cores.py -k plan_review -q` against
     the WP's base commit and observe it fail with the actual current output —
     `["Not all work packages are approved or done"]` — not a false-red from a typo. Name the
     test with `plan_review` in it so the `-k plan_review` filter (used above, and in Review
     Guidance) keeps matching it.
  2. In the same file, add a test (name it with `plan_research_guard` in it, e.g.
     `test_plan_research_guard_absent_and_present`) for `mission_family="plan",
     step_id="research"` covering both branches: `research.md` absent →
     `["Required artifact missing: research.md"]`; `research.md` present
     (`present_artifacts=frozenset({"research.md"})`) → `[]`. **Only the absent-artifact
     assertion is a genuine RED pin at the base commit** (TASKS-VERIFY-001 fix — corrected from
     an earlier draft of this WP that claimed both assertions were RED): `evaluate_guards`
     currently returns `[]` unconditionally for `mission_family="plan", step_id="research"`
     regardless of `research.md`'s presence (falls through to `_evaluate_software_dev_guards`'s
     bare `return []` default, since `"research"` is not one of software-dev's own step ids) —
     so the absent-artifact assertion proves RED (today it wrongly returns `[]` instead of the
     missing-artifact message), while the present-artifact assertion **already passes at the base
     commit**, for the wrong reason (the unconditional fallthrough, not real
     artifact-presence logic), and only becomes a meaningful assertion once T003/T004 land. Keep
     both assertions in the same test (the present-case one is a legitimate companion
     target-shape assertion, just not itself a RED pin) — do not present the present-case
     assertion as proof of RED in the Activity Log or PR description.
  3. **5-way branch completeness for `_evaluate_plan_guards`** (TASKS-VERIFY-003 fix — direct-
     dispatch coverage for the `specify` artifact-presence branch (User Story 2 Acceptance
     Scenario 2) plus hardening coverage, beyond spec.md's literal Acceptance Scenarios, for the
     `plan` artifact-presence branch and the fail-closed else branch, previously uncovered by any
     T001/T002 step). Empirically verified this session:
     unlike `review`/`research` above, `evaluate_guards(_snapshot(mission_family="plan",
     step_id="specify"))` and `...step_id="plan"` **already return the correct post-fix values
     at the base commit** (`["Required artifact missing: spec.md"]` / `[]`, and
     `["Required artifact missing: plan.md"]` / `[]`, respectively) — `mission_family="plan"`
     isn't special-cased in today's `evaluate_guards`, so it falls through to
     `_evaluate_software_dev_guards`, whose own `specify`/`plan` branches happen to run the exact
     same `_check_artifact_present` check `_evaluate_plan_guards` will run. **Do not add a
     full-dispatch `evaluate_guards(...)` assertion for `specify`/`plan` here** — it would be
     exactly the coincidental-pass defect TASKS-VERIFY-001 found for `research`'s present-case,
     just for two more branches. Instead, pin these two branches (plus the fail-closed else
     branch) by calling the new `_evaluate_plan_guards` function **directly**, mirroring T002
     step 1's own idiom for a symbol that doesn't exist yet:
     - Add `test_plan_guard_specify_and_plan_branches_direct_dispatch`: call
       `cores._evaluate_plan_guards(_snapshot(mission_family="plan", step_id="specify"))` and the
       `step_id="plan"` equivalent, both absent- and present-artifact cases. **RED today via
       `AttributeError`** — `_evaluate_plan_guards` does not exist until T003 lands (empirically
       confirmed: `hasattr(cores, "_evaluate_plan_guards")` is `False` at base). Once T003 lands,
       assert `== ["Required artifact missing: spec.md"]` / `== []` for `specify`, and
       `== ["Required artifact missing: plan.md"]` / `== []` for `plan`. This is what actually
       catches an implementer swapping `SPEC_ARTIFACT`/`PLAN_ARTIFACT` between the two branches —
       the exact slip plan.md's Seam & Module Placement section names as a risk — which a
       full-dispatch assertion alone would NOT catch (both branches produce the same shape of
       output via two independent code paths, pre- and post-fix).
     - Add `test_plan_guard_fail_closed_else_branch`: call
       `cores._evaluate_plan_guards(_snapshot(mission_family="plan",
       step_id="not-a-real-plan-action"))`. **RED today via `AttributeError`** (same reason).
       Once T003 lands, assert `== ["No guard registered for plan action:
       not-a-real-plan-action"]`. In the same test, add one companion **full-dispatch**
       assertion: `cores.evaluate_guards(_snapshot(mission_family="plan",
       step_id="not-a-real-plan-action")) == []` at the base commit (falls through to
       `_evaluate_software_dev_guards`'s own catch-all `return []` — empirically confirmed) —
       **this one IS genuinely RED via full dispatch** once T003 lands (target is the fail-closed
       message, not `[]`), and its purpose is different from the direct-call assertion above: it
       confirms `_evaluate_plan_guards` is actually **registered** in `_GUARD_TABLES` under
       `"plan"` (a correct-in-isolation-but-unwired function would pass the direct-call assertion
       and fail this one — the same "isolated, unwired helper" loophole T002 step 2 closes for
       `evaluate_guards_strict`).
  4. **Disk-backed revert-discipline pin for the `research.md` presence tag** (TASKS-VERIFY-002
     fix). None of steps 1-3 above, nor T002, exercise the real
     `gather_artifact_presence(...)` function that actually reads `_PRESENCE_FILE_TAGS` — they
     all construct `ArtifactPresenceSnapshot` by hand via `_snapshot(...)`, so T004's one-line
     addition (`"research.md"` to `_PRESENCE_FILE_TAGS`) would be undetectable if reverted. In
     `tests/runtime/test_bridge_io.py`, add `test_gather_artifact_presence_reads_research_md_presence`,
     mirroring the existing `test_gather_artifact_presence_reads_file_presence` pattern exactly
     (same file, same `_stub_guard_helpers(monkeypatch)` helper): write a real `research.md` file
     to `tmp_path`, call `io_seam.gather_artifact_presence(tmp_path, mission_family="plan",
     step_id="research")`, and assert `"research.md" in snapshot.present_artifacts`. **RED today**
     — empirically confirmed this session: the file exists on disk, but
     `_PRESENCE_FILE_TAGS` does not include `"research.md"` yet, so `present_artifacts` comes back
     empty. This assertion is what T004's own Validation bullet (below) actually points at.
  5. Do **not** add a companion "assert today's actual output" pin anywhere in steps 1-4 above —
     each genuinely-RED assertion's target-shape alone is sufficient proof of the flip (this is
     the exact PLAN-VERIFY-002 fix: no passing-at-base assertion is committed AS THE PROOF of a
     "RED" commit; a passing-at-base companion assertion may still appear alongside a genuine RED
     pin — as in step 2's present-case — but must be labeled as a companion, never as the RED
     evidence itself).
- **Files**: `tests/runtime/test_bridge_cores.py`, `tests/runtime/test_bridge_io.py`.
- **Validation**: every RED assertion named above fails at the WP's base commit for the stated
  reason (steps 1, 3's `AttributeError`s, 3's fail-closed full-dispatch case, and 4); every
  companion passing-at-base assertion (step 2's present-case) is not treated as RED evidence; all
  assertions pass once T003/T004 land.

### T002 — RED: FR-011 ATDD pin (unregistered-family fall-through, 3 assertions)

- **Purpose**: Pin the previously-uncovered fall-through itself — zero tests exist today (per
  spec.md FR-011's own grep-verified claim) that feed an unregistered `mission_family` to either
  call path.
- **Steps**:
  1. **Strict lookup raises** — in `tests/runtime/test_bridge_cores.py`, add a test (name it
     with `unregistered_mission_family_raises` in it, e.g.
     `test_evaluate_guards_strict_raises_for_unregistered_mission_family`) calling
     `cores.evaluate_guards_strict(_snapshot(mission_family="totally-unregistered-family",
     step_id="review"))` inside `pytest.raises(cores.UnregisteredMissionFamilyError)`. RED today
     because neither the function nor the exception class exists yet (`AttributeError` — a
     genuine failure for the right reason).
  2. **`_check_cli_guards` propagates via an injection seam** (name the test with
     `unregistered_mission_family_propagates` in it, e.g.
     `test_check_cli_guards_propagates_unregistered_mission_family_error`) — `_check_cli_guards` hardcodes
     `mission_family="software-dev"` (line 797, re-verified post-#3346-rebase; was
     line 692), so no real caller can reach this state today
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
  3. **Composed path returns `[]` + WARNING log** (name the test with
     `unregistered_mission_family_warns` in it, e.g.
     `test_check_composed_action_guard_warns_for_unregistered_mission_family`) — in
     `tests/runtime/test_bridge_composition.py`,
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
- **Validation**: T001's `plan`/`review`, `plan`/`research` (step 2), `plan`/`specify` +
  `plan`/`plan` + fail-closed-else (step 3, both the direct-call and full-dispatch assertions),
  and T002's strict-raise assertion all go GREEN. `ruff check` complexity ≤15 on every new/changed
  function (NFR-003 — `_evaluate_plan_guards`'s 5-way flat chain is far under the ceiling).

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
- **Validation**: T001 step 2's `research.md`-present branch (`[]` when `research.md` is in
  `present_artifacts`) goes GREEN, AND — this is the assertion that actually detects a revert of
  this change (TASKS-VERIFY-002 fix) — T001 step 4's disk-backed
  `test_gather_artifact_presence_reads_research_md_presence` in `tests/runtime/test_bridge_io.py`
  goes GREEN too; do not consider T004 done on step 2 alone. Confirm no existing per-family
  evaluator function reads the `"research.md"` tag (grep for the literal string in
  `runtime_bridge_cores.py` — it must appear nowhere except your new T003 code), so this addition
  is provably additive and does not affect NFR-001's zero-behavior-change guarantee for the three
  already-registered families.
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
  GREEN. Confirm `runtime_bridge.py:983-996`'s thin compat delegate (re-verified
  post-#3346-rebase, shifted +105 lines from 878-891, same code; which forwards to this
  function) needs no change — do not add a duplicate log call there.
- **Parallel?**: Yes, alongside T004/T006 (disjoint files).

### T006 — Legacy path: direct strict call, no catch

- **Purpose**: FR-005, C-002, User Story 3 — the legacy/CLI-native path raises loudly, never
  silently degrades, for an unregistered family, and `_check_cli_guards` itself is the direct
  caller (not an isolated unwired helper).
- **Steps**: In `_check_cli_guards` (`runtime_bridge.py:785-803`, re-verified
  post-#3346-rebase — shifted +105 lines from 680-698, same code), change the last line,
  `return _cores.evaluate_guards(snapshot)` (line 803, was line 698), to `return
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
     tests/runtime/test_bridge_composition.py tests/runtime/test_bridge_io.py -q` — confirm all
     pass, including T001/T002's tests now GREEN, and confirm **zero** existing assertion had to
     change value (SC-004).
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
  `tests/runtime/test_bridge_composition.py`, `tests/runtime/test_bridge_io.py` (primary, this
  WP's own tests), plus `tests/next/`, `tests/specify_cli/next/`,
  `tests/integration/test_custom_mission_runtime_walk.py` (regression surface —
  NFR-001/NFR-002). Do **not** run the full `pytest tests/` suite.
- **Baseline**: 784 passed / 0 failed at `7deadff0a4f3dfd2744b5e1e35680c0d70f4565e` (cited, not
  re-run from scratch — re-run only the same four commands to compare).
- **Revert discipline**: every behavior change in this WP (registry dispatch, the strict/tolerant
  split, `plan`'s guard table, the `research.md` presence tag) has a test added in T001/T002 that
  fails if that specific change is reverted — this is a stated acceptance requirement for this
  WP, not an aspiration. This includes the `research.md` presence tag specifically: T001 step 4
  adds a disk-backed test against the real `gather_artifact_presence` function (not a
  hand-constructed `_snapshot(...)` value) in `tests/runtime/test_bridge_io.py` — a
  hand-constructed snapshot never reads `_PRESENCE_FILE_TAGS`, so it cannot prove this tag's
  addition is covered (TASKS-VERIFY-002 fix; a prior draft of this WP asserted this coverage
  existed when it did not).

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

- Confirm RED→GREEN on this WP's own base→final commit for every T001/T002 assertion (C-011) —
  do not accept prose reasoning alone (TASKS-VERIFY-001 showed this WP's own prose reasoning
  about RED status was wrong once); use the concrete recipe below.
- **Concrete RED-on-base re-verification recipe** (TASKS-VERIFY-005 fix — mechanical, not prose):
  ```
  git worktree add /tmp/review-wp01 kitty/mission-mission-type-guard-registry-01KZY2FG
  cd /tmp/review-wp01
  # Pull in the WP's RED-commit test files (Commit 2, i.e. after T001+T002 land) while leaving
  # production code at the WP's base commit (before Commit 3):
  git checkout <WP01-commit-2-sha> -- tests/runtime/test_bridge_cores.py \
      tests/runtime/test_bridge_composition.py tests/runtime/test_bridge_io.py
  .venv/bin/python -m pytest tests/runtime/test_bridge_cores.py \
      tests/runtime/test_bridge_composition.py tests/runtime/test_bridge_io.py \
      -k "plan_review or plan_research_guard or plan_guard_specify_and_plan_branches or \
plan_guard_fail_closed or research_md_presence or unregistered_mission_family" -q
  # EXPECT: every matched test FAILS. If any of them passes here, it is not a genuine RED pin —
  # do not accept it as one (this is exactly the class of mistake TASKS-VERIFY-001 found).
  # Then re-check the same files at the WP's final commit:
  git checkout <WP01-final-commit-sha> -- .
  .venv/bin/python -m pytest tests/runtime/test_bridge_cores.py \
      tests/runtime/test_bridge_composition.py tests/runtime/test_bridge_io.py \
      -k "plan_review or plan_research_guard or plan_guard_specify_and_plan_branches or \
plan_guard_fail_closed or research_md_presence or unregistered_mission_family" -q
  # EXPECT: every matched test PASSES.
  ```
  (Substitute the WP's actual Commit-2 and final-commit SHAs. The `-k` pattern matches the test
  names mandated in T001/T002's steps above — if the implementer used different names, adapt the
  pattern or run the two files in full and diff the pass/fail set against T001/T002's steps.)
- Confirm the `UnregisteredMissionFamilyError` docstring carries the cross-reference comment
  (PLAN-ARCH-002) and `evaluate_guards`'s docstring carries the tolerant-wrapper guidance note
  (PLAN-VERIFY-005) — both are one-line additions the plan already designed in; their absence is
  a real (if small) finding, not nitpicking.
- Confirm `_check_composed_action_guard` and `_check_cli_guards` are the **direct** callers of
  `evaluate_guards_strict` (grep the diff, don't just read the test names).
- Confirm T001 step 2's present-artifact assertion is documented as a companion, not RED,
  assertion — and confirm T001 step 4's disk-backed `gather_artifact_presence` test for
  `research.md` actually exists and actually calls the real function (not another
  hand-constructed `_snapshot(...)`).
- Confirm no file outside `owned_files` was touched.

## Activity Log

> **CRITICAL**: entries MUST be in chronological order (oldest first, newest last). Append at
> the end.

- 2026-08-13T22:40:00Z – system – Prompt created.
