---
work_package_id: WP02
title: 'Mission reopen/follow-up commands + history view + #1802 closure'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-002
- NFR-004
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2950599"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_mission_reopen.py
- tests/specify_cli/cli/commands/test_mission_follow_up.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/mission_metadata.py
- src/specify_cli/status/views.py
- tests/specify_cli/cli/commands/test_mission_reopen.py
- tests/specify_cli/cli/commands/test_mission_follow_up.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Mission reopen/follow-up commands + history view + #1802 closure

## ⚡ Do This First: Load Agent Profile

Load your assigned implementer profile (recommended `python-pedro`) via the profile-load skill —
governed context, not a bare name — before reading further.

## Objectives & Success Criteria

Ship the operator-facing post-mission surface over WP01's events, render it, and close #1802 honestly.

- `spec-kitty mission reopen <handle> --reason "<text>"` appends `MissionReopened`, clears `merged_*`,
  and (via WP01's classifier) makes the mission actionable; fail-closed when unrecoverable.
- `spec-kitty mission follow-up <handle> (--commit <sha> | --pr <n>)` records an idempotent
  `FollowUpRecorded` attributed to `mission_id`, allowed in any state.
- `post_mission_events` render in the mission lifecycle/history view.
- #1802 reaches honest closure (FR-001/002 delivered, or residual split to a child).

## Context & Constraints

- Read: `plan.md` (IC-02, IC-03), `contracts/mission-lifecycle-commands.md` (the binding shapes +
  the concrete fail-closed predicate), `data-model.md`, `research.md` (D-A2..D-A5), quickstart §A.
- Commands attach to the EXISTING `spec-kitty mission` group in `cli/commands/mission_type.py`
  (alongside list/current/info/create/run) — `mission.py` is its shim; no `__init__.py` change.
- **Ownership:** do NOT edit `status/lifecycle.py`'s classifier (WP01 owns it). Here you only
  *render* `post_mission_events` via `status/views.py`, and clear `merged_*` via `mission_metadata.py`.
- Re-open must NOT cascade WP lane edits — actionability is WP01's event-driven classification.
- Resolve handles through declared authorities (`mission_id`/`mid8`/slug → feature_dir);
  ambiguous → structured `MISSION_AMBIGUOUS_SELECTOR`; never a silent slug guess (NFR-004).

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T005 – ATDD: failing command tests
- Write failing tests in `test_mission_reopen.py` / `test_mission_follow_up.py`: reopen clears
  merged_* + emits event + mission reads actionable; reopen fail-closed on unrecoverable
  (meta.json absent/corrupt OR branch in neither local nor any remote); follow-up idempotency;
  follow-up allowed in any state; handle ambiguity → MISSION_AMBIGUOUS_SELECTOR.

### T006 – `mission reopen` subcommand
- Add `@app.command("reopen")` to `mission_type.py`: required `--reason`, detect actor, append
  `MissionReopened` (WP01 helper), clear `merged_*` via a `mission_metadata.py` helper.
- **Fail-closed predicate (per contract):** unrecoverable = meta.json absent/corrupt OR the mission
  branch resolves in neither local repo nor any configured remote (use the `core/vcs`/`git_ops`
  lookup). A missing worktree dir alone is recoverable → not fail-closed. On unrecoverable: exit
  non-zero, structured error + remediation, no event, no metadata change.

### T007 – `mission follow-up` subcommand
- Add `@app.command("follow-up")`: exactly one of `--commit <40-hex>` / `--pr <int>` (validate);
  append `FollowUpRecorded` (idempotent dedup via WP01 helper); allowed in any mission state.

### T008 – Handle resolver
- Implement/locate the handle→feature_dir resolver (`mission_id`/`mid8`/slug), disambiguating by
  `mission_id`; ambiguous → `MISSION_AMBIGUOUS_SELECTOR`. Reuse existing resolution helpers where
  present; name it explicitly if net-new.

### T009 – History rendering
- In `status/views.py`, render `post_mission_events` (chronological) with actor/reason (reopen) and
  commit/PR (follow-up) in the mission lifecycle/history surface.

### T010 – #1802 closure
- Confirm FR-001/FR-002 deliver #1802's epic scope; if any residual remains, draft a fresh scoped
  child ticket (do not silently absorb). Prepare the issue-matrix #1802 row for a terminal verdict
  at accept (the orchestrator sets it at the merge gate — do not edit issue-matrix here).

## Test Strategy

- `pytest tests/specify_cli/cli/commands/test_mission_reopen.py tests/specify_cli/cli/commands/test_mission_follow_up.py`
  green. Diff-scoped ruff + mypy --strict on the three source files (exit 0). Paste into handoff.

## Definition of Done

- Both commands work end-to-end; fail-closed + idempotency proven; history renders; #1802 closure
  plan recorded; ruff+mypy clean; new code invoked from the live `spec-kitty mission` group.

## Risks

- Editing WP01's classifier (don't). Silent slug fallback (forbidden). Cascading WP lane edits on
  reopen (forbidden). The Typer group name nuance (`mission`/`mission-type`) — verify the command
  appears under `spec-kitty mission`.

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Verify fail-closed predicate matches the contract, no WP-lane
  cascade, idempotency holds, and #1802 closure is honest (delivered or split, not absorbed).

## Activity Log

- 2026-06-13T17:24:43Z – claude:opus:python-pedro:implementer – shell_pid=2871059 – Assigned agent via action command
- 2026-06-13T17:38:23Z – claude:opus:python-pedro:implementer – shell_pid=2871059 – WP02 done: mission reopen + follow-up commands + post-mission history renderer. Rebased onto target (clean). Tests 15/15 green; status suite 346 pass. ruff exit 0; mypy --strict whole-tree CI invocation exit 0 for the 4 changed src files. Fail-closed: meta.json absent/corrupt OR branch in neither local nor any remote (missing worktree alone recoverable). follow-up idempotent. #1802 FR-001/FR-002 fully delivered, no residual.
- 2026-06-13T17:39:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=2920720 – Started review via action command
- 2026-06-13T17:44:13Z – user – shell_pid=2920720 – CHANGES REQUESTED (cycle 1). BLOCKING: tests/architectural/test_no_dead_symbols.py fails on this lane — WP02's wiring of emit_mission_reopened/emit_follow_up_recorded made WP01's allowlist entries stale; remove lines 633-634. NON-BLOCKING: dead+drifted constant _MERGE_FIELDS_FOR_REOPEN (mission_type.py:810, missing merged_push, unused) delete it; agent/status.py edit is unowned-but-correct T009 wiring (coordination noted). PASS: fail-closed predicate matches contract exactly, event-driven reopen + no WP-lane cascade, idempotency, MISSION_AMBIGUOUS_SELECTOR, history renderer live-wired. views.py:64 needs NO cast — proven follow_imports=skip artifact: canonical SC-6 gate 'mypy --strict src/specify_cli/status/' reports 0 errors for views.py (line 64 only appears in isolated single-file run). Pre-existing PathValidationError failure reported, not WP02's.
- 2026-06-13T17:44:56Z – claude:sonnet:python-pedro:implementer – shell_pid=2935697 – Started implementation via action command
- 2026-06-13T17:49:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2935697 – cycle1: dead-symbol ratchet cleared (helpers now live); dead constant removed; tests green
- 2026-06-13T17:49:30Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2950599 – Started review via action command
- 2026-06-13T17:51:43Z – user – shell_pid=2950599 – cycle1 re-review PASS: dead-symbol ratchet cleared (emit_mission_reopened/emit_follow_up_recorded now live callers in mission_type.py, _CATEGORY_C_WP_IN_FLIGHT_POST_MISSION_LIFECYCLE frozenset removed); dead constant _MERGE_FIELDS_FOR_REOPEN deleted; _safe_load_meta annotation added (type-only, behavior-preserving); 15/15 tests green; ruff exit 0; mypy --strict src/specify_cli/status/ shows 0 errors on views.py (the single-file no-any-return is a follow_imports=skip artifact, not WP02's); PathValidationError is unrelated pre-existing (paths.py untouched by this mission); cross-file coordination noted (test_no_dead_symbols.py + agent/status.py edits outside owned_files are rationale-backed)
