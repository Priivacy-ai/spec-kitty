---
work_package_id: WP06
title: 'Regression envelope: no new blocking states'
dependencies:
- WP05
requirement_refs:
- FR-006
- NFR-003
- NFR-004
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 6 - Envelope
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_charter_blocking_envelope.py
create_intent:
- tests/architectural/test_charter_blocking_envelope.py
execution_mode: code_change
owned_files:
- tests/architectural/test_charter_blocking_envelope.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Regression envelope

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

This mission changes a gate that **blocks people from working**. The failure mode to guard against is
obvious and severe: fixing one blocking state while introducing another. A project that worked before
and refuses to implement afterwards is a worse outcome than the bug we set out to fix.

NFR-003 states it as a bound: the count of blocking states after the change is **same or lower**,
never higher.

## ⚠️ The measurement trap

**You cannot prove "no new blocking states" by measuring only after the change.** A single
post-change measurement tells you what blocks now, not what changed. The baseline must be captured
against the **pre-mission commit**.

Use the mission's merge base. Establish it from the mission metadata / git history rather than
assuming — then evaluate all four shapes there, record the results, and compare against the same
four shapes on the mission tip.

## Objectives & Success Criteria

Complete when:

1. The four-shape blocking matrix is measured on the pre-mission baseline **and** the mission tip.
2. The blocking count is proven same-or-lower, never higher.
3. Greenfield (no charter at all) is proven still advisory and non-blocking.
4. Zero new uncaught exception paths on any diagnostic surface.

## Context & Constraints

The four fixture shapes (`data-model.md`), with expected treatment:

| # | Shape | Before | Expected after |
|---|---|---|---|
| F1 | No charter at all | not blocking | **not blocking** (FR-006) |
| F2 | Legacy bundle, no `charter.yaml` | blocking, ineffective remediation | blocking, **effective** remediation |
| F3 | `charter.yaml` valid | not blocking | not blocking |
| F4 | `charter.yaml` unparseable | blocking | blocking |

Note F2 stays blocking — that is correct. The mission does not make the project healthy; it makes the
instruction work. What changes is that the operator can now get out.

**NFR-004**: diagnostics degrade to a reported state rather than raising to the operator. A surface
that throws a traceback at someone whose charter is malformed has failed, even if it never "blocks".

**Reuse the fixture builders** from WP01's `_fixtures.py` extension. Do not author a third set.

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`

---

## Subtasks

### T027 — Build the four-shape matrix, before and after

**Purpose**: the measurement that makes NFR-003 checkable rather than asserted.

**Steps**:
1. Determine the mission's merge base commit. Do not guess it — derive it.
2. Evaluate all four fixture shapes against the **baseline**: for each, record whether
   implementation is blocked, and what the operator is told.
3. Evaluate all four against the **mission tip**, recording the same.
4. Produce a comparison table. This table is the deliverable — it will be quoted in the mission
   review and the PR.
5. Consider whether the baseline arm can be captured as committed evidence (recorded expected values
   with the commit they came from) rather than a live checkout at test time. A test that shells out
   to another commit is fragile; a recorded baseline with provenance is honest and stable. Choose
   deliberately and say why.

**Files**: `tests/architectural/test_charter_blocking_envelope.py` (new)

**Validation**:
- The baseline is identified by commit SHA, with provenance recorded
- The table covers all four shapes on both arms

### T028 — Assert same-or-lower, never higher

**Steps**:
1. Assert the count of blocking shapes after ≤ the count before.
2. Assert per-shape, not only in aggregate — an aggregate count could stay level while one shape
   silently swapped its blocking status with another. Per-shape comparison catches that; a total
   does not.
3. Make the failure message name **which** shape newly blocks. A bare count mismatch is a bad
   failure message on a gate this important.

**Files**: `tests/architectural/test_charter_blocking_envelope.py`

**Validation**:
- Making any currently-passing shape block turns this red, naming that shape

### T029 — Assert greenfield stays advisory

**Purpose**: FR-006 — the single most likely regression. Every change in this mission makes charter
resolution *stricter*; the greenfield case is what strictness tends to catch by accident.

**Steps**:
1. Assert F1 (no charter at all, never initialised) does not block implementation.
2. Assert its treatment is advisory — the operator is informed, not stopped.
3. Assert this against the real gate path, not a unit-level check that bypasses the runner.

**Files**: `tests/architectural/test_charter_blocking_envelope.py`

**Validation**:
- F1 does not block, exercised through the real gate path
- The test would catch a change that made F1 blocking

### T030 — Assert zero new uncaught exception paths

**Purpose**: NFR-004 — a diagnostic that raises at the operator has failed even if it never blocks.

**Steps**:
1. For each of the four shapes, exercise every operator-facing diagnostic surface WP04 converged.
2. Assert none raises an uncaught exception. Each must return a reported state.
3. Pay attention to F4 (unparseable `charter.yaml`) — malformed input is where a resolver is most
   likely to throw, and it is a state a real operator can reach.
4. Include the `--json` surface: a traceback where structured output was promised breaks any script
   consuming it.
5. **Include `charter context --include section:<id>` explicitly.** Before WP04, this path raised
   `ValueError("No charter.md found for section selector.")` — the mission's clearest NFR-004
   violation, on a path the compact-mode renderer actively tells operators to run. Assert it now
   reports rather than raising, on every shape.

**Files**: `tests/architectural/test_charter_blocking_envelope.py`

**Validation**:
- Every surface returns a state for every shape; none raises
- F4 specifically exercised on every surface

---

## Definition of Done

- [ ] Four-shape matrix measured on both the identified baseline and the mission tip
- [ ] Baseline commit SHA recorded with provenance
- [ ] Blocking count proven same-or-lower per shape, not only in aggregate
- [ ] Failure messages name the offending shape
- [ ] F1 proven non-blocking through the real gate path
- [ ] No uncaught exceptions on any surface for any shape, `--json` included
- [ ] Fixture builders reused from `_fixtures.py`, not re-authored
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base

## Reviewer Guidance

1. **Verify the baseline is real.** If the "before" column was reasoned about rather than measured,
   reject — the whole WP is the measurement. Confirm the baseline commit is identified and that the
   recorded values came from it.
2. **Check per-shape, not aggregate.** An aggregate-only assertion can pass while one shape newly
   blocks and another stops blocking. Confirm the comparison is per-shape.
3. **Try to break it**: make F1 blocking locally and confirm the test goes red naming F1.
4. **Verify F4 is exercised on every surface**, including `--json`. It is the shape most likely to
   throw and it is reachable by real operators.
5. **Confirm fixture reuse.** A third parallel fixture mechanism is a `DIRECTIVE_044` violation.
