---
work_package_id: WP05
title: OriginFlow decision-ledger verbs (open/resolve/defer/cancel)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-012
- NFR-001
- NFR-002
- NFR-005
- C-001
- C-003
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_decision_verbs.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_decision_verbs.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
tracker_refs: []
---

# WP05 — open/resolve/defer/cancel-decision orchestrator-api verbs (Mechanism A)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add four new orchestrator-api verbs — `open-decision`, `resolve-decision`,
`defer-decision`, `cancel-decision` — wrapping
`src/specify_cli/decisions/service.py`'s four pure functions 1:1, matching
the existing host-CLI `spec-kitty agent decision open|resolve|defer|cancel`
subcommands, gated by the `OriginFlow` scope guard (FR-012).

## Context

**Mechanism A only (spec Clarification 3 — do not confuse with WP08's
Mechanism B)**: this WP covers `decisions/index.json`-ledger decisions
keyed by `origin` (`OriginFlow.CHARTER`/`SPECIFY`/`PLAN`,
`src/specify_cli/decisions/models.py:36-41` — only three members, no
`tasks`/`analyze`). It is unrelated to WP08's `answer-decision`
(run-snapshot `pending_decisions`, no `OriginFlow` concept at all) —
C-003 does not bound WP08's verb, and FR-012's `INVALID_ORIGIN_FLOW`
rejection must NOT be applied to `answer-decision`.

**Service functions to wrap** (all in `src/specify_cli/decisions/service.py`,
already wrapped 1:1 by the host CLI's `decision_app`,
`src/specify_cli/cli/commands/decision.py`):
- `open_decision(repo_root, mission_slug, *, origin_flow: OriginFlow,
  input_key, question, options=(), step_id=None, slot_key=None, actor,
  dry_run=False, decision_id=None, on_minted=None) -> DecisionOpenResponse`
  (`service.py:260`)
- `resolve_decision(...)` (`service.py:528`)
- `defer_decision(...)` (`service.py:575`)
- `cancel_decision(...)` (`service.py:612`)

Read the host CLI's own wrapping (`decision.py:213-444`, `cmd_open`/
`cmd_resolve`/`cmd_defer`/`cmd_cancel`) for the exact argument mapping and
error-response shaping (`_open_response_to_dict`, `_terminal_response_to_dict`,
`_handle_decision_error`) — your orchestrator-api verbs should call the
SAME `decisions/service.py` functions the host CLI calls, translating
their responses into `make_envelope`/`_fail` shape rather than reusing
`decision.py`'s own CLI-output helpers directly (those are CLI-layer
presentation code, not a service seam this mission needs to cross into —
unlike FR-014's seam, there is no operator ruling requiring extraction
here; a parallel, independent translation to the orchestrator-api envelope
is the correct layering, matching how `start-review` independently shapes
its own `data` dict rather than reusing `next_cmd.py`'s print helpers).

**FR-012 — OriginFlow scope guard (all four verbs)**: reject any
`--origin` value outside `{charter, specify, plan}` with a structured
`error_code` (e.g. `INVALID_ORIGIN_FLOW`) BEFORE calling into
`decisions/service.py` — never let an invalid origin reach the service
layer and get silently accepted or misfiled.

**Terminal-transition rejection (Edge Cases, spec.md)**: `resolve-decision`
on an already-`resolved`/`cancelled` decision must reject with the SAME
structured error the host-CLI `decision_app resolve` subcommand already
raises for an invalid terminal-state transition — call
`resolve_decision` and let its own `DecisionError` propagate through
`_fail`, do not add a redundant pre-check that could drift from the
service layer's own validation.

**C-001**: confirm no `spec-kitty-events`/`spec-kitty-tracker` import
introduced.

## Subtask T022: RED — author `test_decision_verbs.py`

**Purpose**: Land failing ATDD tests before any of the four verbs exist.

**Steps**:
1. Create `tests/specify_cli/orchestrator_api/test_decision_verbs.py`.
2. Write tests for spec User Story 3's four acceptance scenarios:
   - `open-decision --mission --origin specify <question payload> --policy`
     → `success: true`, `data.decision_id`, ledger `status: open`.
   - `resolve-decision --mission --decision-id <id> <answer payload> --policy`
     → `success: true`, `data.status: resolved`, ledger updated on disk.
   - `defer-decision`/`cancel-decision` → corresponding service function
     invoked, ledger reflects new status.
   - A `--mission` whose current phase is `tasks`/`analyze` combined with
     an origin outside `{charter, specify, plan}` → `INVALID_ORIGIN_FLOW`
     structured error.
   - Terminal-transition rejection: `resolve-decision` on an
     already-resolved/cancelled decision → structured error, not a
     silent no-op success.
3. Mark `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` —
   these tests read/write a real `decisions/index.json` ledger against a
   real mission fixture dir; `fast`-marked would be invisible to
   `integration-tests-core-misc`'s collection filter.
4. Confirm RED on `planning_base_branch`.

**Files**: `tests/specify_cli/orchestrator_api/test_decision_verbs.py` (new, ~180-250 lines).

**Validation**: fails (command not found) on `planning_base_branch`.

## Subtask T023: Implement `open-decision` verb (FR-006)

**Purpose**: Wrap `open_decision`.

**Steps**:
1. `@app.command(name="open-decision")`, options `--mission`, `--origin`
   (validated against `{charter, specify, plan}` before calling the
   service — FR-012), `--input-key`, `--question`, `--options` (repeatable
   or comma-separated — match `decision.py:213-306`'s own flag shape),
   `--step-id`/`--slot-key` (mutually exclusive, mirror the service
   function's own "supply step_id OR slot_key" contract), `--actor`,
   `--policy` (required — mutating verb).
2. Call `open_decision(...)`, translate `DecisionOpenResponse` into
   `data` (`decision_id`, `status`), envelope via `make_envelope`/`_fail`.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~50-70 new lines).

**Validation**: T022's open-decision scenario passes.

## Subtask T024: Implement `resolve-decision` verb (FR-007)

**Purpose**: Wrap `resolve_decision`, including terminal-transition rejection.

**Steps**:
1. `@app.command(name="resolve-decision")`, options `--mission`,
   `--decision-id`, answer payload option(s) (mirror `cmd_resolve`'s own
   flags), `--policy` (required).
2. Call `resolve_decision(...)`; let a `DecisionError` on an
   already-terminal decision propagate to `_fail` with the same
   `error_code` the host-CLI raises (read `_handle_decision_error` in
   `decision.py:179` for the exact code/message mapping to preserve).

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~40-50 new lines).

**Validation**: T022's resolve-decision and terminal-rejection scenarios pass.

## Subtask T025: Implement `defer-decision` / `cancel-decision` verbs (FR-008/FR-009)

**Purpose**: Wrap `defer_decision`/`cancel_decision`.

**Steps**:
1. `@app.command(name="defer-decision")` and `@app.command(name="cancel-decision")`,
   each mirroring `cmd_defer`/`cmd_cancel`'s own flags, `--policy` required.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~50-70 new lines combined).

**Validation**: T022's defer/cancel scenarios pass.

## Subtask T026: FR-012 OriginFlow guard — shared validation helper

**Purpose**: Avoid duplicating the `{charter, specify, plan}` check four
times with drift risk between copies.

**Steps**:
1. Write ONE small private helper (e.g. `_validate_origin_flow_or_fail(cmd,
   origin: str) -> OriginFlow`) used by all four verbs — parses/validates
   `--origin` against `OriginFlow`'s three members, `_fail(cmd,
   "INVALID_ORIGIN_FLOW", ...)` on mismatch, returns the validated
   `OriginFlow` enum member otherwise.
2. Call this helper from `open-decision` (the only one of the four that
   actually MINTS a new decision's origin — `resolve`/`defer`/`cancel`
   operate on an EXISTING decision_id, whose origin was already validated
   at open time; confirm from `service.py`'s function signatures whether
   `resolve_decision`/`defer_decision`/`cancel_decision` even take an
   `origin_flow` parameter at all, and only wire the guard into whichever
   verbs actually receive one — do not invent an `--origin` flag on a verb
   whose service function doesn't need it).

**Files**: part of `commands.py`'s WP05 diff (no separate file).

**Validation**: T022's `INVALID_ORIGIN_FLOW` scenario passes; confirmed the
guard is applied only where the service layer's own signature requires it.

## Subtask T027: Negative-path coverage + NFR-001 re-run

**Purpose**: NFR-002/SC-004 negative paths + confirm zero regression to
existing verbs.

**Steps**:
1. Extend `test_commands_fail_closed.py`/`test_typed_error_fail_closed.py`
   with: missing `--policy` on each of the four verbs; invalid `--origin`;
   `--decision-id` naming a nonexistent decision.
2. Re-run full existing `tests/specify_cli/orchestrator_api/` suite.

**Files**: `test_commands_fail_closed.py`, `test_typed_error_fail_closed.py` (extended).

**Validation**: new cases pass; existing suite green (NFR-001).

## Write-Scope / Adjacent Open PRs

`orchestrator_api/commands.py` — same-file overlap with **PR #3826**
(merge-mission area) and with sibling WPs WP03/WP04/WP06/WP08 (mutually
independent per plan.md's parallel-lane design); marked
`scope: codebase-wide` for the same reason as WP03/WP04 (see WP03's
Write-Scope note for the full mechanism explanation). **PR #3826 merged
into `main` on 2026-09-02**; this mission's branch has not yet rebased
onto that merge as of this tasks phase, so `commands.py`'s merge-mission
area on `main` already carries #3826's changes. Sequence the MERGE of
this WP against its siblings, and re-verify `commands.py` against
`main`'s current state (not the now-stale #3826-still-open assumption).

## Definition of Done

- [ ] RED commit: `test_decision_verbs.py` fails on `planning_base_branch`.
- [ ] `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` on the new test file.
- [ ] All four verbs implemented, calling the exact `decisions/service.py`
      functions the host CLI calls — no reimplemented ledger logic.
- [ ] FR-012 guard applied via one shared helper, not four copies.
- [ ] Terminal-transition rejection confirmed to reuse the service layer's
      own `DecisionError`, not a redundant pre-check.
- [ ] Negative-path additions land; existing suite green.
- [ ] `mypy --strict` / `ruff check` clean.
- [ ] `grep` confirms zero `spec-kitty-events`/`spec-kitty-tracker` reference introduced.

Run: `spec-kitty agent action implement WP05 --agent <name>`

## Risks

- **FR-012 guard drift**: four independent copies of the origin check
  would be a real drift risk if written separately — T026 exists
  specifically to prevent that; do not let the implementation regress to
  four copies for "simplicity."
- **Same-file merge collision** — see Write-Scope note.

## Reviewer Guidance

- Confirm all four verbs call `decisions/service.py`'s functions directly
  — reject any orchestrator-api-layer reimplementation of ledger
  read/write logic.
- Confirm the FR-012 guard is a single shared helper.
- Confirm `resolve-decision`'s terminal-transition rejection error code
  matches the host-CLI `decision_app resolve` subcommand's own code
  (`decision.py:179`'s `_handle_decision_error` mapping) — a drifted code
  string is a real, easy-to-miss regression here.
