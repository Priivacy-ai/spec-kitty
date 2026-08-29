---
work_package_id: WP03
title: Close the runner's remediation backfill
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-003
- C-001
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 3 - Close the defect class
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/preflight/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/preflight/runner.py
- src/specify_cli/charter_runtime/preflight/result.py
- tests/specify_cli/charter_preflight/test_runner.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Close the runner's remediation backfill

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

## Why this WP exists

WP02 fixed the reported P0. This WP closes the **class**, which is what `DIRECTIVE_043` and C-001
actually require.

`src/specify_cli/charter_runtime/preflight/runner.py:245`:

```python
f"{check.name} {check.state}; run `{check.remediation or 'spec-kitty charter status'}`"
```

When a check emits **no** remediation, the runner substitutes `spec-kitty charter status` — a status
reporter, which by construction cannot change any check's state. This is structurally identical to
BC-2, except it sits on the *default* path rather than one branch. Fixing only the reported instance
and leaving this would defer the next occurrence rather than close the class.

It also makes the spec's US1 Acceptance Scenario 3 currently **unsatisfiable**: that scenario
requires an exempt check to emit no remediation, but the runner guarantees the operator is always
shown a command.

## Objectives & Success Criteria

Complete when:

1. A check emitting no remediation produces operator output containing **no command**.
2. The exemption set declared in WP01 is wired into the runner's output path as real data.
3. WP01's assertions cover the runner's composed output for the exempt case.

## Context & Constraints

**Do not degrade a confusing message into a silent one.** The operator still needs to know the check
failed and why. What must go is the *fabricated command*, not the diagnostic information. A blocked
reason that names the check and its state, with no `run …` clause, is the target — not an empty
string.

**Careful with the `blocked_reason` shape.** `result.py` carries an output-shape pin: `blocked_reason`
stays a single `str`, with multiple lines newline-joined. Do not change that contract.

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`

---

## Subtasks

### T013 — Remove the remediation backfill

**Purpose**: stop fabricating a command the operator cannot use.

**Steps**:
1. Read `runner.py` around `:235-250` to understand how `blocked_reason` is composed and what
   `_PASS_STATES` filters.
2. Change the composition so a check with `remediation is None` produces a line that reports the
   check and state **without** a `run …` clause.
3. Keep the shape contract: `blocked_reason` remains a single `str`; multiple non-passing checks are
   newline-joined as before.
4. Grep the file for any other place a default remediation is injected. If there is more than one,
   fix them all — a second backfill elsewhere would leave the class open.

**Files**: `src/specify_cli/charter_runtime/preflight/runner.py`

**Validation**:
- A `None`-remediation check yields a line with no command
- A check *with* a remediation is unchanged — same text as before
- `blocked_reason` is still a single `str`

### T014 — Wire the exemption set into the runner path

**Purpose**: make "this check has no self-service remediation" an explicit, reviewable declaration
rather than an accident of a `None` field (C-EFF-2).

**Steps**:
1. Take the exemption-set structure WP01 declared in the enforcement mechanism and give it a real
   home the runner (or the check registry) can consult.
2. Membership must be explicit. A check is exempt because it is declared exempt — never because it
   happened to return `None`.
3. **The exemption set is NO LONGER empty — WP02 found two genuine members.** This obligation was
   added after WP02 completed:

   `_compute_charter_source`'s `invalid` state (`:318`) and `_compute_synced_bundle`'s cascading
   `stale` state (`:357`) have **no effective self-service remediation**. WP02 proved this
   exhaustively: `charter generate` (with and without `--no-from-interview`, with and without
   `--force`, with and without a prior `charter interview --defaults`), `spec-kitty upgrade --yes`,
   and `charter synthesize` were each tried against a fixture with unparseable `charter.yaml`. Every
   write path in the codebase merges into the existing file via a round-trip YAML parse, so all of
   them require it to already parse. None can repair syntactically broken YAML. This is an
   architectural gap, not a search failure.

   WP02 deliberately left them pointing at `spec-kitty charter generate` with an honest `detail`
   rather than emitting `None`, because emitting `None` *before* T013 removes the runner backfill
   would hand the operator `spec-kitty charter status` instead — equally unable to help. The two
   changes are only safe together, which is why they are both in this WP.

   **Your obligation**: make `:318` and `:357` emit `remediation=None`, declare them in the exemption
   set, update the pinned exemption count (WP01 pins it at 0 — it becomes 2, a deliberate reviewed
   change you must call out in your handoff), and ensure their operator-visible output explains the
   situation without naming a command. `computer.py` is WP02's file — this is a narrow, justified
   out-of-map edit; record a one-line rationale.

   After your work, WP01's mechanism should be fully green: the two cases stop being effectiveness
   failures because they are no longer remediation-emitting.

4. Do not invent any *other* exemption members. These two are evidenced; anything else needs the
   same standard of proof.
4. Make sure the pinned exemption-set size in WP01 still matches after your change. If your work
   legitimately changes the count, update the pin **and** say so explicitly in the handoff — that is
   a deliberate reviewed act, not a silent adjustment.

**Files**: `src/specify_cli/charter_runtime/preflight/runner.py`,
`src/specify_cli/charter_runtime/preflight/result.py` (only if the shape genuinely requires it)

**Validation**:
- The exemption set is visible as data, in one place
- Nothing infers exemption from a `None` remediation

### T015 — Extend WP01's assertions to the composed output

**Purpose**: the enforcement must now bind the surface this WP changed.

**Note on ownership**: WP01's test file is not in this WP's `owned_files`. Extending it here is an
intentional, narrow out-of-map edit — record a one-line rationale in your handoff note. Do not
restructure or weaken anything already there; only add.

**Steps**:
1. Add coverage asserting that for an exempt check, the runner's composed `blocked_reason` contains
   no command.
2. Add coverage asserting the backfill cannot return: changing the removed fallback back to a
   hardcoded command must turn the mechanism red.

**Files**: `tests/architectural/test_remediation_effectiveness.py` (narrow addition, out-of-map)

**Validation**:
- Re-introducing the backfill turns the mechanism red
- WP01's existing assertions and floors are untouched

### T016 — Verify exempt output contains no command

**Purpose**: prove the spec's US1 Acceptance Scenario 3 is now satisfiable.

**Steps**:
1. Using a fixture, drive a check into a non-passing state with no remediation and declared exempt.
2. Assert the operator-visible output names the check and its state.
3. Assert the output contains no `run …` clause and no command string.
4. Assert the operator is not left with an empty or uninformative message.

**Files**: `tests/specify_cli/charter_preflight/test_runner.py`

**Validation**:
- Output is informative and command-free
- Existing `test_runner.py` cases still pass — this file already exercises missing/invalid/blocked
  states with remediation assertions, and several will need their expectations updated where the
  fabricated command used to appear

---

## Definition of Done

- [ ] `runner.py` no longer fabricates a remediation for `None`-remediation checks
- [ ] No other backfill site remains in the file
- [ ] Exemption set is explicit data consulted by the runner path
- [ ] `blocked_reason` is still a single `str` with newline-joined lines
- [ ] WP01's mechanism covers the composed output; re-introducing the backfill turns it red
- [ ] Exempt-check output is informative and contains no command
- [ ] Existing `test_runner.py` expectations updated where the fabricated command used to appear
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base

## Reviewer Guidance

1. **Re-introduce the backfill locally** and confirm WP01's mechanism goes red. If it stays green,
   T015 did not actually bind the composed output and this must be rejected.
2. **Check the exempt message is not silent.** Read the actual output text. "Nothing" is not the
   target; "the check failed, here is which and why, and there is no self-service fix" is.
3. **Verify exemption is declared, not inferred.** Grep for anything that treats `remediation is
   None` as equivalent to exempt — that is exactly the loophole C-EFF-2 closes.
4. **Check the out-of-map edit to WP01's test file** is narrow and additive, with a recorded
   rationale. Weakening or restructuring existing assertions there must be rejected.
5. **Verify the shape pin** in `result.py` is intact.
