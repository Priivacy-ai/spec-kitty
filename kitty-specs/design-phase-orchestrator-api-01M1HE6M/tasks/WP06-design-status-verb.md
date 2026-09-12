---
work_package_id: WP06
title: design-status read-only query verb
dependencies:
- WP01
requirement_refs:
- FR-010
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_design_status.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_design_status.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
tracker_refs: []
---

# WP06 — design-status read-only query verb

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add a read-only `design-status` orchestrator-api verb (FR-010) that
mirrors `list-ready`'s "no state transition, no event emission" pattern
for the design pipeline: `current_phase`, `next_action`, `open_decisions`.

## Context

**Decision (deliberate, not an oversight — spec Clarification 6, do not
re-derive)**: `design-status` does **NOT** delegate to
`resolve_next_workflow_action` (`_internal_runtime/planner.py`) or the
fuller `decide_next`/`_resolve_next_unified_step` engine
(`runtime_bridge.query_current_state`). Both existing engines return a
WP-loop/run-state-shaped payload (`action`, `wp_id`, `prompt_file`), not
FR-010's four design-phase fields, and `decide_next`'s query path
materializes/reads a runtime run (`get_or_start_run`) as a side effect —
this read-only status verb must NOT depend on that side effect.

`design-status` instead defines a **narrow, design-phase-only reduction**
over:
- on-disk artifact presence: `spec.md` exists? `plan.md` exists?
  `tasks/` finalized (mirror whatever check `finalize-tasks` itself uses
  to determine "finalized" — e.g. presence + a finalization marker/commit,
  not merely a non-empty directory)? `analysis-report.md` exists?
- the `decisions/index.json` ledger, for `open_decisions`.

This is the SAME shape of deliberate narrowing `list-ready` already
applies (reducing WP state without invoking the full FSM transition
validators) — a documented, examined choice, not an unexamined drift risk.

**Response shape** (spec User Story 4 Acceptance Scenarios):
- `data.current_phase`: e.g. `"specify"`, `"plan"`, `"tasks"`, `"analyze"`.
- `data.next_action`: names the VERB the host should call next (e.g.
  `"plan"`, `"tasks"`, `"check-prerequisites"`).
- `data.open_decisions`: list of `{decision_id, origin}` for any open
  entries in the ledger — when non-empty, `next_action` indicates
  resolution is required before the phase can advance.
- **No `--policy` required** — read-only, mirrors `list-ready`'s existing
  no-policy contract.
- **Idempotency (Acceptance Scenario 4, binding)**: repeated calls against
  an unchanged mission return BYTE-IDENTICAL `current_phase`/`next_action`
  fields — no state transition, no event emission, ever.

## Subtask T028: RED — author `test_design_status.py`

**Purpose**: Land failing ATDD tests across the four named fixture states
before the verb exists.

**Steps**:
1. Create `tests/specify_cli/orchestrator_api/test_design_status.py`.
2. Write four fixture-state tests (spec Acceptance Scenarios 1-3 + Edge
   Cases): (1) only `spec.md` scaffolded → `current_phase: "specify"`,
   `next_action` names `plan`; (2) an open, unresolved decision moment →
   `open_decisions` lists it, `next_action` indicates resolution required;
   (3) `tasks/` finalized, `analysis-report.md` absent →
   `current_phase`/`next_action` indicate `analyze` is next, naming
   `check-prerequisites`; (4) idempotency — two consecutive calls against
   an unchanged mission produce byte-identical `current_phase`/
   `next_action`.
3. Add a nonexistent-mission-slug negative test → structured `error_code`
   (mirroring `_resolve_mission_dir_or_fail`'s existing pattern).
4. Mark `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` —
   real fixture-mission artifact presence/absence across four distinct
   on-disk states requires real fixture setup, not a `fast`-eligible
   pure-mock test.
5. Confirm RED on `planning_base_branch`.

**Files**: `tests/specify_cli/orchestrator_api/test_design_status.py` (new, ~160-220 lines).

**Validation**: fails (command not found) on `planning_base_branch`.

## Subtask T029: Implement the narrow read-only reduction

**Purpose**: The core FR-010 logic — in-file, no new engine.

**Steps**:
1. Write a private reduction helper in `commands.py` (e.g.
   `_reduce_design_status(mission_dir: Path) -> dict`) that: checks
   `spec.md`/`plan.md`/`tasks/`-finalized/`analysis-report.md` presence in
   order to derive `current_phase` and `next_action`; reads
   `decisions/index.json` for `open_decisions` (any entry with
   `status: open`, regardless of phase — an open decision from an earlier
   phase still blocks, per Acceptance Scenario 2).
2. Do NOT import or call `resolve_next_workflow_action` or `decide_next`/
   `runtime_bridge.query_current_state` — this is a hard constraint from
   Clarification 6, not a style preference; a reviewer should reject any
   import of either.
3. Determine "tasks/ finalized": read the same signal `finalize-tasks`
   itself writes/checks (do not invent a new heuristic — check
   `mission_finalize.py` for what marks a `tasks/` dir as finalized, e.g. a
   `commit_hash` written to `wps.yaml` or a lane-computation artifact, and
   reuse that signal).

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~70-100 new lines).

**Validation**: T028's four fixture-state tests pass.

## Subtask T030: Wire into `commands.py` as `@app.command`

**Purpose**: Register the verb.

**Steps**:
1. `@app.command(name="design-status")`, options `--mission` only (no
   `--policy`).
2. `validate_outbound_payload(data, "orchestrator_api")` then
   `make_envelope`/`_emit` — same pattern as every other verb.

**Files**: part of T029's diff.

**Validation**: verb callable end-to-end.

## Subtask T031: Idempotency test (Acceptance Scenario 4)

**Purpose**: Prove no state transition, no event emission.

**Steps**:
1. Call `design-status` twice against the same unchanged mission fixture;
   assert `current_phase`/`next_action` fields are byte-identical.
2. Additionally assert no NEW entry was appended to `mission-events.jsonl`
   or any lifecycle-record store between the two calls (a stronger check
   than field-identity alone — this is what actually proves "no event
   emission," not just "same-looking output").

**Files**: part of `test_design_status.py`.

**Validation**: test passes.

## Subtask T032: Negative-path + NFR-001 re-run

**Purpose**: Fail-closed on a nonexistent mission; confirm zero
regression.

**Steps**:
1. Extend `test_commands_fail_closed.py`/`test_typed_error_fail_closed.py`
   with the nonexistent-mission-slug case for `design-status`.
2. Re-run full existing `tests/specify_cli/orchestrator_api/` suite.

**Files**: `test_commands_fail_closed.py`, `test_typed_error_fail_closed.py` (extended).

**Validation**: new case passes; existing suite green.

## Write-Scope / Adjacent Open PRs

`orchestrator_api/commands.py` — same-file overlap with **PR #3826**
(merge-mission area) and with sibling WPs WP03/WP04/WP05/WP08 (mutually
independent per plan.md's parallel-lane design); marked
`scope: codebase-wide` for the same reason as WP03/WP04/WP05 (see WP03's
Write-Scope note for the full mechanism explanation). **PR #3826 merged
into `main` on 2026-09-02**; this mission's branch has not yet rebased
onto that merge as of this tasks phase, so `commands.py`'s merge-mission
area on `main` already carries #3826's changes. Sequence the MERGE of
this WP against its siblings, and re-verify `commands.py` against
`main`'s current state (not the now-stale #3826-still-open assumption).

## Definition of Done

- [ ] RED commit: `test_design_status.py` fails on `planning_base_branch`.
- [ ] `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` on the new test file.
- [ ] `design-status` implemented as a narrow, in-file reduction — zero
      import of `resolve_next_workflow_action` or `decide_next`/
      `query_current_state`.
- [ ] Idempotency proven via both field-identity AND zero-new-event-log-entry
      assertions.
- [ ] No `--policy` required (read-only, matches `list-ready`'s contract).
- [ ] Negative-path case added; existing suite green.
- [ ] `mypy --strict` / `ruff check` clean.

Run: `spec-kitty agent action implement WP06 --agent <name>`

## Risks

- **Engine-delegation temptation**: reaching for
  `resolve_next_workflow_action`/`decide_next` because "it already computes
  something similar" is the most likely implementation mistake here —
  Clarification 6 explicitly rejected this; a reviewer must check for it.
- **Same-file merge collision** — see Write-Scope note.

## Reviewer Guidance

- Grep the WP06 diff for `resolve_next_workflow_action`/`decide_next`/
  `query_current_state`/`get_or_start_run` — any hit is a Clarification 6
  violation, reject the WP.
- Confirm the idempotency test checks event-log/lifecycle-record
  non-mutation, not just output-field equality.
- Confirm `tasks/`-finalized detection reuses `finalize-tasks`'s own
  signal rather than a new ad hoc heuristic.
