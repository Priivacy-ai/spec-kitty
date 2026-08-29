---
work_package_id: WP02
title: Correct the charter-source remediation (turns WP01 green)
dependencies:
- WP01
requirement_refs:
- FR-002
- C-004
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - The P0 fix
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/freshness/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/freshness/computer.py
- tests/specify_cli/charter_freshness/test_computer.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Correct the charter-source remediation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status`).
- **You must address all feedback** before your work is complete.

---

## This is the P0 fix

An operator on a legacy-bundle project is blocked from implementing anything. The gate tells them to
run `spec-kitty charter sync`. That command is documented as never writing anything —
`src/charter/sync.py:18`: *"it always reports `synced=False` / `files_written=[]`"*. Every return
path passes `files_written=[]`; the former `synced=True` branch is dead code
(`cli/commands/charter/sync.py:42`).

So the operator runs it, nothing changes, the gate refuses with the identical message. Forever.
Issue #2831, escalated to P0.

**WP01 has already proven this structurally.** Its mechanism is currently RED, failing on exactly the
four states you are about to fix. Your job is to make it green *by correcting the remediation* — not
by touching WP01's assertions or floors.

## Objectives & Success Criteria

Complete when:

1. All four `spec-kitty charter sync` remediations are replaced with instructions that actually clear
   the states emitting them.
2. WP01's mechanism goes red → green **with its pinned floors unchanged**.
3. An operator on a legacy-bundle fixture reaches an unblocked implement step following only the
   instructions the tool emits, and the step count is recorded.

## Context & Constraints

**C-004 is binding — the migration is inherited, not redefined.** The consolidation migration that
genuinely repairs a legacy-bundle project already exists and works. You may point operators at it.
You must **not** reimplement it, alter its behaviour, or fork its logic into the freshness computer.

**What the intended remediation always was.** `charter/bundle.py:199`'s docstring for
`first_missing_bundle_file` describes this exact scenario and names the defect site:

> *"…this returns that path when the bundle has not been generated yet — the fail-loud chokepoints
> raise an actionable 'run the migration / charter generate' error instead of silently persisting an
> un-healable `None` bundle-content hash that the freshness reader
> (`specify_cli.charter_runtime.freshness.computer`) would report as permanently `stale`."*

So the intended instruction was *run the migration / charter generate* — never `charter sync`. The
freshness computer was simply never routed through this seam.

**Do not fix this by lowering WP01's floor.** If a state resists correction, that is a finding to
report, not a number to nudge.

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`
- Use the workspace path `spec-kitty agent action implement WP02` gives you.

---

## Subtasks

### T008 — Determine the effective remediation per state

**Purpose**: establish, empirically, which command clears each of the four states — before changing
any string.

The four sites (R-005):

| Producer | Line | State |
|---|---|---|
| `_compute_charter_source` | `:309` | `missing` — `charter.yaml` absent |
| `_compute_charter_source` | `:318` | `invalid` — `charter.yaml` present, unparseable |
| `_compute_synced_bundle` | `:348` | (see the function) |
| `_compute_synced_bundle` | `:357` | (see the function) |

**Steps**:
1. For each state, build the fixture that exhibits it (WP01's T001 builders).
2. Try each candidate command against the fixture and observe whether the state changes:
   - `spec-kitty upgrade` (runs the consolidation migration — the repro established this works for
     the legacy-bundle case)
   - `spec-kitty charter generate` / `charter synthesize`
   - any other command the codebase already exposes
3. Record which command clears which state, with the observed before/after states.
4. **Different states may need different commands.** `missing` and `invalid` are different problems;
   do not assume one string serves both.

**Files**: investigation only — no production edit in this subtask

**Validation**:
- Every claim is backed by an observed state change in a fixture, not by reading a docstring
- If a state has *no* effective self-service remediation, say so — that makes it an exemption-set
  candidate, which is a WP03 concern, and must be reported rather than papered over

### T009 — Replace the remediation on `_compute_charter_source`

**Purpose**: correct the two states that constitute the reported P0.

**Steps**:
1. Replace `remediation="spec-kitty charter sync"` at `:309` (`missing`) and `:318` (`invalid`) with
   the commands T008 proved effective.
2. Keep the `detail` field's explanatory text accurate — if the remediation changes, the explanation
   around it must still be true.
3. Do not change the `state` values. The state vocabulary is not this WP's concern (that is WP05).

**Files**: `src/specify_cli/charter_runtime/freshness/computer.py`

**Validation**:
- WP01's assertions for these two states flip to green
- `_compute_charter_source`'s docstring still accurately describes its behaviour

### T010 — Replace the remediation on `_compute_synced_bundle`

**Purpose**: the same defect on the second producer. These emit the same ineffective string and are
part of the same class — leaving them would mean WP01 stays red.

**Steps**:
1. Replace the `charter sync` remediations at `:348` and `:357` with the commands T008 proved
   effective for those states.
2. Same constraints as T009: keep `detail` accurate, do not touch state values.

**Files**: `src/specify_cli/charter_runtime/freshness/computer.py`

**Validation**:
- WP01's assertions for these two states flip to green
- No remaining `spec-kitty charter sync` remediation anywhere in the file

### T011 — Verify WP01 goes red → green with floors unchanged

**Purpose**: prove the fix fixed the proven defect, and only that.

**Steps**:
1. Run WP01's mechanism. It must now pass.
2. Diff WP01's test file against its state at the end of WP01. **It must be unchanged.** If you had
   to edit it to get green, that is a finding — report it rather than committing the edit.
3. Confirm the pinned floors still read 7 states / 3 producers / exemption-set size unchanged.
4. Update `tests/specify_cli/charter_freshness/test_computer.py` where it asserts the old
   remediation strings — those assertions are now wrong and should assert the new values.

**Files**: `tests/specify_cli/charter_freshness/test_computer.py`

**Validation**:
- WP01's file has zero diff attributable to this WP
- The freshness computer's own tests assert the corrected strings

### T012 — End-to-end walkthrough; record the SC-002 step count

**Purpose**: SC-002 — prove an operator gets from blocked to unblocked using only what the tool tells
them, and replace the spec's deliberately-unnumbered "bounded number of steps" with the real count.

**Steps**:
1. Build the F2 fixture (legacy bundle, no `charter.yaml`) — the mission's trigger state.
2. Run the preflight gate. Record the exact message and the emitted command.
3. Execute **only** that command. No external knowledge, no manual file edits.
4. Re-run the gate. If still blocked, follow the new instruction. Repeat.
5. Record the number of steps to reach an unblocked implement step.
6. If the loop does not terminate, that is a failure of this WP — report it, do not adjust the
   fixture until it passes.

**Files**: test coverage for the walkthrough belongs in
`tests/specify_cli/charter_freshness/test_computer.py` or a new fixture-driven test; keep it within
this WP's owned files.

**Validation**:
- The walkthrough terminates in an unblocked state
- The step count is recorded in the handoff note for the plan's SC-002 update

---

## Definition of Done

- [ ] All four `charter sync` remediations replaced with commands proven effective in T008
- [ ] Zero occurrences of `spec-kitty charter sync` as a remediation value in the file
- [ ] WP01's mechanism is GREEN, with its file unchanged and floors unchanged
- [ ] `test_computer.py` asserts the corrected remediation strings
- [ ] SC-002 walkthrough terminates; step count recorded in the handoff note
- [ ] The consolidation migration is untouched (C-004)
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base

## Reviewer Guidance

1. **Verify the red-first evidence is intact.** Check out WP01's tip, run its mechanism, confirm red.
   Then check out this WP, run it, confirm green. If WP01 was already green at its own tip, the
   red-first discipline was broken and this must be rejected.
2. **Verify WP01's test file has zero diff from this WP.** Any edit to it is the classic
   move-the-goalposts failure and must be rejected.
3. **Verify each new remediation empirically.** Do not accept "it should work" — build the fixture,
   run the command, observe the state change yourself for at least the two `_compute_charter_source`
   states.
4. **C-004**: grep the diff for any change to the consolidation migration. There must be none.
5. **Check the `detail` strings** still describe reality. A corrected command with a stale
   explanation next to it is half a fix.
