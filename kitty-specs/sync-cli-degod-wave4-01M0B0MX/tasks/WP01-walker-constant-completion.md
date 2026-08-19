---
work_package_id: WP01
title: Walker campsite — complete the named-constant set
dependencies: []
requirement_refs:
- FR-005
- NFR-003
planning_base_branch: refactor/wave4-sync-degod
merge_target_branch: refactor/wave4-sync-degod
branch_strategy: Planning artifacts for this mission were generated on refactor/wave4-sync-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/wave4-sync-degod unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
history:
- Created by /spec-kitty.tasks (Wave-4 sync degod)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/calibration/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/calibration/walker.py
- tests/calibration/test_walker.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile before anything else: `/ad-hoc-profile-load python-pedro`. Then run
`spec-kitty charter context --action implement --json` and apply the resolved
directives/tactics. State in your first status note which directives/tactics you applied
(expect the campsite directive `DIRECTIVE_025` and the smallest-viable-diff tactic to be
front-of-mind here).

## Objective

`src/specify_cli/calibration/walker.py` holds `_REQUIRED_SCOPE`, a curated
`dict[(mission_key, action_urn) -> frozenset[str]]` of doctrine URNs. The module began
hoisting the repeated URN string literals into named module constants (see L48-57:
`DIRECTIVE_003`, `DIRECTIVE_010`, `DIRECTIVE_037`, the three `TACTIC_*` names, the three
`AGENT_PROFILE_*` names) but the set is **partial** — the majority of the URNs inside the
`software-dev` and `research` frozensets are still raw inline string literals, so Sonar
`S1192` (repeated string literal ≥3×) still fires ~14 times on the file. Worse, two names
that WERE hoisted have been **re-inlined** at their use sites (`DIRECTIVE_010` inside the
`review` frozenset at L150; `DIRECTIVE_037` at L157 uses the raw `"directive:DIRECTIVE_037"`
instead of the existing `DIRECTIVE_037` constant).

Complete the named-constant set and route every use site through the constant, driving
`S1192` to **0** on this file with **byte-identical** runtime behavior. This is a pure
campsite slice — it is **independent of the sync degod** (different package, different
guard), so it can land day-one in its own lane, in parallel with everything else.

## Read first (source of truth)

The mission plan.md (the IC map — IC-01 "Mechanical campsite", and the "WP-translation
guards" §, esp. guard #5: *only `walker.py` is genuinely pre-golden*), the contract
(`contracts/sync-cli-characterization-contract.md`), `data-model.md` (the `_REQUIRED_SCOPE`
lookup-table entity + INV byte-stability), `research/squad-findings-post-plan.md` (finding
Pr-4). This is a Wave-4 degod: **zero behavior change**; on this WP the behavior guard is
the frozenset-equality test in `tests/calibration/test_walker.py`, not the sync golden.

## Environment (CRITICAL — worktree vs editable install)

Work in the lane worktree. The repo-root `.venv` editable-install points at the MAIN
checkout, so test YOUR changes with `PYTHONPATH=<worktree>/src`. Define
`VENV=<repo>/.venv/bin; WT=<worktree>`.

Tests (this WP does not touch SaaS/render arms, but keep the recipe uniform):

```
PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  $VENV/python -m pytest tests/calibration/test_walker.py -q -p no:cacheprovider
```

Lint/type + the S1192 verification:

```
$VENV/ruff check $WT/src/specify_cli/calibration/walker.py
$VENV/mypy --strict $WT/src/specify_cli/calibration/walker.py
# S1192 proof — expect zero hits scoped to this file:
$VENV/ruff check --select S1192 $WT/src/specify_cli/calibration/walker.py
```

NEVER run the full suite or `uv run` (a bare `uv run` re-syncs and destroys the hand-built
`.venv`; see the CLAUDE.md UI-e2e note). Real-port/daemon tests are irrelevant here.

## Subtasks

### T001 — Complete the named-constant set

**Purpose**: introduce a module constant for every doctrine URN that appears ≥3× (or is
part of a family we standardize) across `_REQUIRED_SCOPE`, matching the existing
`<KIND>_<ID>` / `TACTIC_<NAME>` / `AGENT_PROFILE_<NAME>` naming already present at L48-57.

**Steps** (add the constants in the existing block around L48-57, keeping alphabet/kind
grouping consistent with what is there):

- Directive URNs still inline in the `implement`/`review`/`tasks` frozensets (L134-163):
  add `DIRECTIVE_024 = "directive:DIRECTIVE_024"`, `DIRECTIVE_025`, `DIRECTIVE_028`,
  `DIRECTIVE_029`, `DIRECTIVE_030`, `DIRECTIVE_034` (verbatim `"directive:DIRECTIVE_0NN"`
  values — copy the exact strings from the current frozensets; do not guess).
- Tactic / toolguide URNs: add named constants for `"tactic:acceptance-test-first"`,
  `"tactic:quality-gate-verification"`, `"tactic:stopping-conditions"`,
  `"tactic:autonomous-operation-protocol"`, `"tactic:change-apply-smallest-viable-diff"`,
  `"tactic:tdd-red-green-refactor"`, `"toolguide:efficient-local-tooling"`,
  `"tactic:problem-decomposition"` (the last already recurs in `plan`/`tasks`). Follow the
  `TACTIC_<UPPER_SNAKE>` / `TOOLGUIDE_<UPPER_SNAKE>` convention.
- Action-URN prefixes: the `("software-dev", "action:software-dev/<x>")` keys repeat the
  `"action:software-dev/"` fragment. Add constants for the three action URNs that recur
  (`action:software-dev/implement`, `.../specify`, `.../retrospect`) so the tuple keys read
  through a name. (Only hoist where the literal genuinely repeats ≥3× — do not over-hoist a
  key that appears once.)
- Agent-profile URNs surfaced in the `research` frozensets that recur: add
  `AGENT_PROFILE_RESEARCHER_ROBBIE = "agent_profile:researcher-robbie"` and
  `AGENT_PROFILE_CURATOR_CARLA = "agent_profile:curator-carla"` alongside the existing
  three `AGENT_PROFILE_*` constants.

**Files**: `src/specify_cli/calibration/walker.py` (constant block only).

**Validation**: `ruff check --select S1192` count trends toward 0; module still imports.

### T002 — Route every use site through the constant; fix the 2 re-inlined constants

**Purpose**: an added constant is inert until the frozenset entries reference it. Replace
the raw URN literals inside `_REQUIRED_SCOPE` (L109-end) with the T001 names, and repair the
two regressions where an already-defined constant was bypassed.

**Steps**:

- In each frozenset value, swap the raw `"directive:…"`, `"tactic:…"`, `"toolguide:…"`,
  `"agent_profile:…"` strings for the matching named constant from L48-57 (existing) + T001
  (new).
- **Fix the re-inlined pair**: at L150 the `review` frozenset lists
  `"directive:DIRECTIVE_010"` — replace with the existing `DIRECTIVE_010` constant. At L157
  it lists `"directive:DIRECTIVE_037"` — replace with the existing `DIRECTIVE_037`
  constant. These two are the "fix the 2 re-inlined existing constants" targets called out
  in the IC map.
- Do **not** alter the *value* of any frozenset — the set membership must be identical
  before/after. This is a literal→name substitution only; a constant must equal the exact
  string it replaces.

**Files**: `src/specify_cli/calibration/walker.py` (`_REQUIRED_SCOPE` body).

**Validation**: `ruff check --select S1192` reports **0** on the file; `mypy --strict`
clean.

### T003 — Confirm the frozenset-equality guard is green

**Purpose**: prove byte-identical behavior. `tests/calibration/test_walker.py` asserts the
resolved required-scope frozensets by equality; a name/value mismatch or an accidental set
change fails it.

**Steps**:

- Run the walker test (env recipe above). If a case fails, the substitution changed a set —
  revert that specific literal to its exact prior value; do **not** edit the test to match a
  changed set.
- If the existing test does not already pin every `(mission_key, action_urn)` entry you
  touched, add a focused equality assertion for the newly-constant-backed keys so the guard
  actually covers the substitution (Sonar new-code-coverage expectation for touched lines).
- Run `ruff` + `mypy --strict` one final time.

**Files**: `tests/calibration/test_walker.py` (only if a covering assertion is missing —
otherwise read-only confirmation).

**Validation**: `test_walker.py` green; `ruff`/`mypy` clean; `S1192` = 0.

## Branch Strategy

Planning/base + merge target: `refactor/wave4-sync-degod`. The execution worktree is
allocated per the computed lane from `lanes.json` (`spec-kitty implement WP01` prepares it)
— do not reconstruct the path. This is **lane-a** (independent; no degod dependency), so it
may run concurrently with WP02.

## Definition of Done

- [ ] Every doctrine URN that recurs ≥3× in `_REQUIRED_SCOPE` is a named module constant
      following the existing `L48-57` convention.
- [ ] The two re-inlined constants (`DIRECTIVE_010` L150, `DIRECTIVE_037` L157) route
      through their existing constants.
- [ ] `ruff check --select S1192 walker.py` = **0**; full `ruff check` clean.
- [ ] `mypy --strict walker.py` clean (zero issues/warnings; no new suppressions).
- [ ] `tests/calibration/test_walker.py` frozenset-equality green — **byte-identical**
      required-scope sets pre/post.
- [ ] No frozenset membership changed; diff is literal→name only.

## Reviewer Guidance

Verify the WP-translation guards that bind this WP:

- **Guard #5**: this is the only genuinely pre-golden slice — confirm it touches
  `calibration/` only and does **not** reach into `sync.py` (no cross-contamination with the
  chain lane).
- **Byte-identical (INV-1 analogue)**: diff each frozenset value name-by-name against the
  string it replaced; the constant's value must equal the prior literal exactly. Reject any
  set membership delta.
- Confirm no constant was *added but left unused* (that would leave `S1192` partially unfixed
  and add dead names). Confirm the two re-inlined constants are genuinely fixed at L150/L157.
- Confirm the guard test actually exercises the substituted keys (not a vacuous pass).
