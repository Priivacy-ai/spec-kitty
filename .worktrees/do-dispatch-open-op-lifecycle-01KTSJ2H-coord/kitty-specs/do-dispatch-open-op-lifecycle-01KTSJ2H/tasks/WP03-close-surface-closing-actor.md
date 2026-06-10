---
work_package_id: WP03
title: Close Surface and Closing Actor
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "46633"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/advise.py
- tests/specify_cli/invocation/test_invocation_e2e.py
- tests/specify_cli/invocation/cli/test_complete.py
role: implementer
tags: []
---

# WP03 — Close Surface and Closing Actor

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Thread the closing actor through the canonical close path: `ProfileInvocationExecutor.complete_invocation()` gains a required `closed_by` parameter (`"agent"` | `"doctor_sweep"`), the `profile-invocation complete` CLI passes `"agent"`, idempotent double close is preserved, and close-time auto-commit is the only moment an Op record is committed. This is the single close implementation the WP04 sweep will reuse.

## Context

- Spec: FR-003, FR-012. Data model invariants 2-4. WP01 introduced `OpCompletedEvent` with required `closed_by` and left a hardcoded `closed_by="agent"` at the executor construction site for you to replace.
- Current close path: `executor.complete_invocation()` (`src/specify_cli/invocation/executor.py:258-315`) — reads started mode for the evidence gate (FR-009 mode gate: advisory/query refuse evidence), appends completed event, appends artifact/commit links, calls `_commit_op_record()` (best-effort auto-commit, `executor.py:428-451`, uses `safe_commit` with `allow_completed_op_on_protected_branch=True`).
- CLI entry: `complete_invocation()` in `src/specify_cli/cli/commands/advise.py:251-310` (`profile-invocation complete`).
- `ask`/`advise` semantics are untouched — they already leave Ops open and print the close instruction.

## Subtasks

### T011 — `closed_by` in the executor close path

**Purpose**: every close records who closed.

**Steps**:
1. Add `closed_by: Literal["agent", "doctor_sweep"]` parameter to `complete_invocation()` (keyword-only, no default — callers must be explicit; this is the sanctioned breaking change C-001).
2. Construct `OpCompletedEvent` with it; remove the WP01 hardcode + note.
3. Preserve untouched: evidence mode gate ordering (gate check before any write), `AlreadyClosedError` from the writer, artifact/commit link appends, propagator submission of the completed event.
4. Grep all callers (`grep -rn "complete_invocation" src tests`) and update each explicitly — expected: the CLI command (T012) and tests. If WP02 already merged, `do_cmd.py` has no call left; if you find one, the lane base is stale — stop and report rather than re-adding.

**Validation**: mypy --strict forces every caller to pass `closed_by`; e2e test asserts the written line contains `"closed_by": "agent"`.

### T012 — CLI close passes `closed_by="agent"`

**Purpose**: the manual/agent close surface is explicit.

**Steps**:
1. In `advise.py`'s `complete_invocation` command, pass `closed_by="agent"`. Do NOT expose a `--closed-by` CLI flag — the sweep is the only other closer and it calls the executor directly (WP04).
2. Error handling unchanged: `InvalidModeForEvidenceError`, `AlreadyClosedError`, missing-invocation errors keep their structured output and exit codes; `--json` mode emits structured error objects.

**Validation**: CLI integration test closes an Op, asserts `closed_by` in the record; double close exits 1 with the structured already-closed error in both rich and JSON modes.

### T013 — Close-time auto-commit semantics

**Purpose**: open Ops stay visible as untracked files; closed Ops are durably committed (FR-012).

**Steps**:
1. Verify (and pin with tests — likely no code change): `_commit_op_record()` runs only from `complete_invocation()`, never from `invoke()`. Commit message format `op(<profile-id>): <action> [<id8>]` unchanged; it reads profile/action from the **started** event (`_read_started_event`) — confirm that helper survived WP01's reader updates.
2. Auto-commit failures stay best-effort: logged at WARNING, never raise, close still succeeds (existing contract — keep it).
3. Confirm the commit includes the evidence dir when `--evidence` was used (if it does today, keep; if it never did, do not add — note it in the PR description instead).

**Validation**: e2e test: after close, `git log -1 --format=%s` matches `op(...): ... [...]`; before close, the JSONL file is untracked.

### T014 — Close-surface tests

**Purpose**: pin outcomes, gates, idempotency, commits.

**Steps**: extend `tests/specify_cli/invocation/test_invocation_e2e.py` and create `tests/specify_cli/invocation/cli/test_complete.py` covering: each outcome value written verbatim; evidence accepted for task_execution, refused for advisory/query (`InvalidModeForEvidenceError` before any write); double close idempotent error; artifact + commit links still appended after the completed event; auto-commit message format; `closed_by="agent"` on CLI closes.

**Validation**: `.venv/bin/pytest tests/specify_cli/invocation -q` green; mypy --strict + ruff clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json`. Implement via `spec-kitty agent action implement WP03 --agent <name>` (depends on WP01).

## Definition of Done

- [ ] `complete_invocation` requires explicit `closed_by`; CLI passes `"agent"`; no CLI flag exposed.
- [ ] Evidence mode gate, link events, idempotent double close, and propagator submission unchanged.
- [ ] Auto-commit happens only at close; message format preserved; open Ops never committed.
- [ ] Tests cover all outcomes/gates; ≥90% coverage on changed code; mypy --strict + ruff clean.

## Risks & Reviewer Guidance

- **Parallel-lane coupling**: WP02 (do_cmd.py) and WP03 (executor.py) touch adjacent code and may run in parallel lanes. Ownership is disjoint by file; if you need to edit `do_cmd.py`, stop — that's WP02's surface.
- **Protected-branch commit exception**: `_commit_op_record` relies on the documented `allow_completed_op_on_protected_branch` path — do not "simplify" it away; ops legitimately close on protected branches.
- **No default for `closed_by`**: a default of `"agent"` would let the WP04 sweep silently misattribute closes. Reviewer: confirm the parameter is keyword-only and default-free.

## Activity Log

- 2026-06-10T21:10:09Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Assigned agent via action command
- 2026-06-10T21:11:54Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Blocked: lane-c base is stale — WP01 (approved) is not merged into the mission branch; executor.py has no OpCompletedEvent/closed_by stopgap and do_cmd.py:153 still calls complete_invocation. WP03 depends on WP01; need lane-a merged into mission branch and lane-c rebased before close-surface work can proceed.
- 2026-06-10T21:27:25Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Ready for review: closed_by threaded, outcome explicit, auto-commit pinned
- 2026-06-10T21:27:58Z – claude:fable:reviewer-renata:reviewer – shell_pid=46633 – Started review via action command
- 2026-06-10T21:31:24Z – user – shell_pid=46633 – Review passed: closed_by threaded keyword-only default-free Literal[agent,doctor_sweep]; outcome required Literal with no None-to-done coercion anywhere; CLI passes closed_by=agent with no --closed-by flag; missing/invalid --outcome exits 2 before any write; double close exits 1 with structured already_closed in rich+JSON; evidence gate ordering, link appends, propagator, best-effort auto-commit op(<profile>): <action> [<id8>] all preserved; 405 tests green, ruff+mypy clean
