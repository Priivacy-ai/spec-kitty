---
work_package_id: WP04
title: Runtime `next` Correctness
dependencies:
- WP03
requirement_refs:
- FR-015
- FR-016
- FR-017
- FR-018
- FR-019
- FR-020
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
- T024
agent: "claude:opus-4-7:reviewer:reviewer"
shell_pid: "1535"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/next/**
- src/specify_cli/status/transitions.py
- src/specify_cli/cli/commands/mark_status.py
- src/specify_cli/dashboard/**
- src/specify_cli/missions/plan/mission-runtime.yaml
- tests/contract/test_next_no_implicit_success.py
- tests/contract/test_next_no_unknown_state.py
- tests/contract/test_plan_mission_yaml_validates.py
- tests/contract/test_mark_status_input_shapes.py
- tests/unit/status/test_review_claim_transition.py
- tests/integration/test_dashboard_counters.py
- tests/integration/test_planning_artifact_wp.py
tags: []
---

# WP04 — Runtime `next` Correctness

## Objective

Make `spec-kitty next` align with its documented decision algorithm. Bare
calls do not advance state. No mission run returns `unknown` mission with
`[QUERY - no result provided]`. Planning-artifact WPs have a first-class
non-worktree execution path. The review-claim transition emits
`for_review -> in_review`. `mark-status` accepts both bare and qualified
WP IDs. Dashboard / progress counters reflect approved / in-review / done
correctly. The shipped `plan` mission's runtime YAML validates against the
runtime schema.

## Context

This WP depends on WP03's canonical-root resolver — the runtime emit path
must read and write to the canonical mission repo. Decisions documented in
`research.md` D2, D3, D4. Contract surface in
[`contracts/runtime-decision-output.md`](../contracts/runtime-decision-output.md).

## Branch strategy

- **Planning base**: WP03 tip.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks

### T018 — Bare `next` does not advance state

**Purpose**: A bare `spec-kitty next` is a query, not an outcome.

**Steps**:

1. In `src/specify_cli/cli/commands/next.py` (or wherever the `next`
   typer command lives), do NOT default `result` to `success` when
   `--result` is omitted. Pass `result=None` to the runtime.
2. In `src/specify_cli/next/_internal_runtime/`, the advance logic
   only fires when `result == "success"`. `result is None` returns the
   current decision without advancing.
3. Add `tests/contract/test_next_no_implicit_success.py`:
   - Build a fixture mission past `specify`. Call `next` with no
     `--result`. Assert `mission_state` is unchanged before and after.

**Validation**:
- New test passes.
- `pytest tests/integration/ -k next` green.

### T019 — Eliminate `unknown` mission state and `[QUERY - no result provided]`

**Purpose**: A valid mission run never returns `unknown` mission with that
placeholder.

**Steps**:

1. Audit prompt templates under
   `src/specify_cli/missions/*/command-templates/` for the literal string
   `[QUERY - no result provided]`. Remove every occurrence; replace with
   either: (a) a concrete query rendered from the mission state, or
   (b) a structured blocked decision.
2. In the runtime decision builder, if the resolver cannot determine
   the mission state for a valid run, return `kind="blocked"` with a
   concrete `reason` (e.g., `"no mission-runtime state file at <path>"`)
   and a populated `guard_failures` list, NOT `mission_state="unknown"`.
3. Add `tests/contract/test_next_no_unknown_state.py`:
   - For a fixture mission with a populated runtime state, assert
     `mission_state != "unknown"` and the decision body does not
     contain the placeholder.
   - For a deliberately broken state file, assert `kind="blocked"` and
     a populated `reason`.

**Validation**:
- `grep -rn "QUERY - no result provided" src/` returns no hits in
  shipped templates.
- New test passes.

### T020 — `execution_mode: planning_artifact` lane-skip path

**Purpose**: Planning-artifact WPs do not block the runtime when no
worktree can be allocated.

**Steps**:

1. Extend the WP frontmatter schema (in
   `src/specify_cli/lanes/planner.py` and the WP loader) to accept
   `execution_mode: "code_change" | "planning_artifact"`. Default
   `"code_change"`.
2. The lane planner skips `planning_artifact` WPs in lane fan-out;
   they execute in the canonical repo with `workspace_path: null`.
3. The runtime decision JSON for a `planning_artifact` WP includes
   `workspace_path: null` and a `notes` field explaining the
   non-worktree execution path.
4. Add `tests/integration/test_planning_artifact_wp.py`:
   - Build a fixture mission with one `code_change` and one
     `planning_artifact` WP.
   - Drive `spec-kitty next`. Assert the planning-artifact WP returns
     a `step` decision with `workspace_path: null` and a non-empty
     `notes` field.

**Validation**:
- Test passes.
- Code-change WPs continue to receive a non-null workspace path.

### T021 — Review-claim transition emits `for_review -> in_review`

**Purpose**: Document and enforce the documented state machine.

**Steps**:

1. In `src/specify_cli/status/transitions.py`, ensure the transition
   matrix permits `for_review -> in_review` (which it already does)
   and that the runtime path uses `to_lane="in_review"` for review
   claims.
2. Audit any code path that emits `for_review -> in_progress` for a
   reviewer — replace with `for_review -> in_review`.
3. Add `tests/unit/status/test_review_claim_transition.py`:
   - Drive a fixture WP through `for_review`. Have a reviewer "claim"
     it. Assert the emitted event's `to_lane == "in_review"`.

**Validation**:
- Test passes.
- `grep -rn 'to_lane.*"in_progress"' src/specify_cli/cli/commands/review*` — no review-claim emits this.

### T022 — `mark-status` accepts bare and qualified WP IDs

**Purpose**: Match the parser to the emitter contract.

**Steps**:

1. In `src/specify_cli/cli/commands/mark_status.py`, accept both
   `WP01` and `<mission_slug>/WP01`. Normalize to bare WP ID before
   calling the transition validator.
2. Add `tests/contract/test_mark_status_input_shapes.py`:
   - Bare ID: `mark-status WP01 to_lane=approved` succeeds.
   - Qualified ID: `mark-status <mission>/WP01 to_lane=approved`
     succeeds.
   - Garbage ID: `mark-status garbage to_lane=approved` raises
     structured error.

**Validation**:
- Test passes.
- No regression in existing `mark-status` integration tests.

### T023 — Dashboard / progress counters

**Purpose**: Counters reflect approved / in-review / done correctly.

**Steps**:

1. Audit `src/specify_cli/dashboard/` for counter computation. Confirm
   all 9 lanes are accounted for and that `approved`, `in_review`,
   `done` each have their own count.
2. Add `tests/integration/test_dashboard_counters.py`:
   - Build a fixture mission, drive WPs to a mix of lanes, snapshot
     `agent tasks status` JSON, assert counters match.

**Validation**:
- Test passes.

### T024 — Validate `plan` mission YAML

**Purpose**: The shipped `plan` mission's runtime YAML must validate.

**Steps**:

1. Locate `src/specify_cli/missions/plan/mission-runtime.yaml`.
2. Locate the runtime YAML schema (likely a Pydantic model or JSON
   schema in `src/specify_cli/next/_internal_runtime/`).
3. Add `tests/contract/test_plan_mission_yaml_validates.py` that loads
   each shipped mission YAML (`plan`, `software-dev`, `research`,
   `documentation`) and asserts each validates against the schema.
4. Fix any actual schema mismatch in `plan/mission-runtime.yaml`.
   Document the fix in `research.md` if it required a non-trivial
   restructure.

**Validation**:
- Test passes for all four shipped mission YAMLs.

## Definition of Done

- All seven subtasks complete with listed validation passing.
- `pytest tests/contract/ -k 'next or plan_mission or mark_status'` green.
- `pytest tests/integration/ -k 'planning_artifact or dashboard_counters'`
  green.
- `pytest tests/unit/status/` green.
- `grep -rn 'QUERY - no result provided' src/` returns 0 hits.

## Risks

- T020 changes the WP frontmatter schema. Migrate existing fixtures /
  templates to accept either form (default `code_change`).
- T024 may surface a real bug in the shipped `plan` mission YAML;
  document the fix carefully.
- T019 must not silence legitimate `mission_state` values that map to
  uninitialized but in-progress runs; the test fixture should cover the
  "no state yet" case explicitly.

## Reviewer guidance

1. T018: read the diff to confirm `result=None` is propagated all the
   way to the advance logic. The contract test pins behavior; the
   reading verifies the path.
2. T019: a quick regex-grep on the source tree for the placeholder
   string is the fastest review tool.
3. T020: verify the lane planner does NOT fan out planning-artifact
   WPs. Look at `planner.py:_fan_out` (or equivalent) and confirm the
   filter.
4. T024: schema drift here is a footgun. Make sure the test loads
   every shipped mission YAML, not just `plan`.

## Activity Log

- 2026-04-26T08:36:09Z – claude:opus-4-7:implementer:implementer – shell_pid=93036 – Started implementation via action command
- 2026-04-26T08:49:53Z – claude:opus-4-7:implementer:implementer – shell_pid=93036 – WP04 ready for review: T018 query mode pinned; T019 placeholder absent; T020 planning_artifact contract pinned; T021 review claim emits for_review->in_review; T022 mark-status accepts qualified IDs; T023 dashboard counters per-lane verified; T024 plan/mission-runtime.yaml validates and strict-xfail demoted.
- 2026-04-26T08:50:35Z – claude:opus-4-7:reviewer:reviewer – shell_pid=1535 – Started review via action command
- 2026-04-26T08:54:17Z – claude:opus-4-7:reviewer:reviewer – shell_pid=1535 – Review passed: 7/7 subtasks (5 verified-already-fixed regressions pinned, 2 real fixes T022 mark-status normalize and T024 plan-mission YAML schema rewrite). 40 new tests green; xfail demotion in tests/next/test_next_command_integration.py correct. Out-of-scope edits limited to mark-status path correction in agent/tasks.py and the xfail demotion; both documented.
