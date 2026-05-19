---
work_package_id: WP01
title: Audit row-family classifier (#1122)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-009
- NFR-001
- C-003
- C-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-unblock-sync-identity-boundary-canary-01KRZJ07
base_commit: 45edd287a01e5a00dedf1d7fb7ba38183ede266e
created_at: '2026-05-19T09:58:15.561787+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "57716"
history:
- at: '2026-05-19T08:46:23Z'
  actor: spec-kitty.tasks
  note: Generated initial WP prompt.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/audit/
execution_mode: code_change
mission_slug: unblock-sync-identity-boundary-canary-01KRZJ07
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/audit/shape_registry.py
- src/specify_cli/audit/detectors.py
- tests/specify_cli/audit/test_detectors_row_family.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

The profile defines your identity, governance scope, and boundaries for this work. Apply it for the entire duration of this work package.

## Pre-flight (charter compliance)

Before opening any code changes:

1. **Assign the tracker ticket to the Human-in-Charge.** This WP traces to GitHub issue [`Priivacy-ai/spec-kitty#1122`](https://github.com/Priivacy-ai/spec-kitty/issues/1122). Per charter rule "HiC assignment for tracker-backed work", assign that issue to the project's HiC before (or as part of) beginning implementation.
2. **If you encounter pre-existing test failures** while running the audit suite (or any test), per charter you MUST open a GitHub issue first — record the failing command, the failure summary, and your evidence that the failure is pre-existing — before treating it as accepted baseline.

## Objective

Stop `spec-kitty agent mission create` from immediately producing `FORBIDDEN_KEY` findings on its own mission-lifecycle event rows. Encode the row-family boundary inside `src/specify_cli/audit/shape_registry.py` so the `FORBIDDEN_KEYS` detector in `src/specify_cli/audit/detectors.py` skips the rule for legitimate lifecycle rows while still flagging genuinely malformed status-transition rows that carry `event_type` / `event_name`.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree is allocated per computed lane from `lanes.json` after `finalize-tasks` runs. Use `spec-kitty agent action implement WP01 --agent <name>` to enter the assigned workspace; do **not** create a worktree manually.

## Context

### What the bug is

`kitty-specs/<mission>/status.events.jsonl` carries two distinct row families written by different subsystems:

1. **Status-transition rows** (`from_lane` / `to_lane`) — written by `src/specify_cli/status/store.py` and friends.
2. **Mission-lifecycle rows** (`aggregate_type="Mission"`, `event_type="MissionCreated|SpecifyStarted|..."`) — written by `src/specify_cli/status/lifecycle_events.py` and several peers (`invocation/propagator.py`, `dossier/`, `next/_internal_runtime/engine.py`, `retrospective/events.py`).

`src/specify_cli/audit/detectors.py:55` currently declares:

```python
FORBIDDEN_KEYS: frozenset[str] = frozenset({"event_type", "event_name"})
```

with a comment claiming `event_type` is a pre-migration leftover. That assumption is wrong for the lifecycle family: those rows **legitimately** discriminate by `event_type`. Result: every fresh mission produces TeamSpace blockers and `spec-kitty sync now` refuses to connect.

### Source contract

See [contracts/audit-row-family.md](../contracts/audit-row-family.md) for the predicate + behavior table.

### Why this approach (not splitting the file)

Decision `01KRZJ2F33SYE86XZDW8JRHA7R` (resolved: `scope_audit_by_row_family`) chose to encode the family boundary in `shape_registry.py` rather than split `status.events.jsonl`. The constraint C-003 forbids the split. Plan decision `01KRZKFW7MKWVDXCXXYAZW47SB` (resolved: `shape_registry_named_shape`) further chose the registry as the boundary contract surface.

## Subtasks

### T001 — Add `is_mission_lifecycle_row` predicate

**Purpose**: Make the row-family boundary first-class in the audit's shape vocabulary.

**Steps**:
1. Open `src/specify_cli/audit/shape_registry.py`. Locate where existing shapes (e.g., `handoff_event_row`) are declared.
2. Add a public predicate:
   ```python
   from collections.abc import Mapping
   from typing import Any

   def is_mission_lifecycle_row(row: Mapping[str, Any]) -> bool:
       """Return True iff `row` matches the mission-lifecycle row family.

       Mission-lifecycle rows carry the lifecycle discriminator `event_type`
       and identify the aggregate via `aggregate_type == "Mission"`. Both
       predicates must hold; either alone does NOT classify as lifecycle.

       Reference: contracts/audit-row-family.md.
       """
       if not isinstance(row, Mapping):
           return False
       if row.get("aggregate_type") != "Mission":
           return False
       event_type = row.get("event_type")
       return isinstance(event_type, str) and bool(event_type)
   ```
3. If the registry exposes a "shape index" data structure (e.g. a dict of `name -> classifier`), also register the named shape `mission_lifecycle_row` so future detectors can consult the registry by name. If no such index exists, leave the predicate as a standalone export — do NOT invent a new structure for this WP.
4. mypy --strict must be clean on the new function.

**Files**:
- `src/specify_cli/audit/shape_registry.py` (modify; ~25 added lines)

**Validation**:
- [ ] `from specify_cli.audit.shape_registry import is_mission_lifecycle_row` succeeds.
- [ ] `mypy --strict src/specify_cli/audit/shape_registry.py` passes.

### T002 — Teach `FORBIDDEN_KEYS` detector to consult the predicate

**Purpose**: Skip the `FORBIDDEN_KEYS` rule for lifecycle rows while preserving it for everything else.

**Steps**:
1. Open `src/specify_cli/audit/detectors.py`. Locate the detector that yields `FORBIDDEN_KEY` findings (around line 55–60).
2. Import the predicate: `from .shape_registry import is_mission_lifecycle_row`.
3. At the top of the detector function (or wherever the per-row loop is), short-circuit when the row is a lifecycle row:
   ```python
   if is_mission_lifecycle_row(row):
       return  # or `continue` if inside a loop — lifecycle rows legitimately carry `event_type`
   ```
4. Do **not** modify the `FORBIDDEN_KEYS` frozenset itself. Do **not** modify the comment on line 56 in a way that contradicts the new behavior — instead, update the comment to reflect the row-family scoping (one or two sentences).
5. Confirm no other detector in `detectors.py` depends on the old "every row is a transition" assumption.

**Files**:
- `src/specify_cli/audit/detectors.py` (modify; ~10 added lines + comment touch-up)

**Validation**:
- [ ] Running the audit against a `status.events.jsonl` that contains only lifecycle rows yields zero `FORBIDDEN_KEY` findings.
- [ ] Running the audit against a `status.events.jsonl` that contains only canonical status-transition rows produces no false-positives (no behavior change).
- [ ] A synthetic row carrying `event_type` but no `aggregate_type` is still flagged.

### T003 — Per-shape regression test matrix

**Purpose**: Pin the detector's behavior to the rows in the contract table so future regressions surface in CI.

**Steps**:
1. Create `tests/specify_cli/audit/test_detectors_row_family.py`.
2. Implement one test per row in the contract table (see [contracts/audit-row-family.md](../contracts/audit-row-family.md), "Behavioral contract"):
   - Status-transition row → no `FORBIDDEN_KEY` finding.
   - Lifecycle row (`aggregate_type=Mission`, `event_type="MissionCreated"`) → no finding.
   - Lifecycle row (`aggregate_type=Mission`, `event_type="SpecifyStarted"`) → no finding.
   - `event_type` present, no `aggregate_type` → **flagged**.
   - `aggregate_type=Mission`, no `event_type` → not flagged (no forbidden key present).
   - Malformed: `from_lane=...`, `to_lane=...`, `event_type=...`, no `aggregate_type` → **flagged**.
3. Each test should construct the row dict in-line and call the detector function directly (no full mission setup required).
4. Use `pytest`; follow existing test conventions under `tests/specify_cli/audit/`.

**Files**:
- `tests/specify_cli/audit/test_detectors_row_family.py` (new; ~90 lines)

**Validation**:
- [ ] `pytest tests/specify_cli/audit/test_detectors_row_family.py` — all 6 cases pass.
- [ ] On a checkout pinned to `rc13`, at least the lifecycle-row cases FAIL (proof the tests are real regressions).

### T004 — End-to-end integration test on fresh mission

**Purpose**: Prove the user-visible reproduction in `#1122` is fixed.

**Steps**:
1. Add an integration test (extending existing audit integration coverage if a file already exists, otherwise inline alongside T003's file or under `tests/specify_cli/cli/`).
2. The test should:
   - Use `tmp_path` to create a tmp project dir.
   - Initialize a Spec Kitty project (using existing test fixtures if available) or simulate the minimum filesystem state needed.
   - Programmatically invoke `spec-kitty agent mission create` (via `CliRunner` or by calling the underlying creator). Use `--mission-type software-dev`.
   - Read the resulting `status.events.jsonl`.
   - Run the audit (call `doctor mission-state --audit` underlying function, or invoke via `CliRunner` and parse JSON).
   - Assert that zero findings have `code == "FORBIDDEN_KEY"`.
3. Skip the test gracefully if existing fixtures don't support the bootstrap; document why in a comment and prefer the direct-detector test from T003 as the primary regression.

**Files**:
- The same test file (or a peer file). Aim for one new test function; ~50 lines.

**Validation**:
- [ ] Test passes after the fix.
- [ ] On rc13 (pre-fix), the test fails with `FORBIDDEN_KEY` findings present.

### T005 — Quality gate: mypy + ruff + suite

**Purpose**: Confirm no collateral regression on the audit package.

**Steps**:
1. Run `mypy --strict src/specify_cli/audit/` from repo root.
2. Run `ruff check src/specify_cli/audit/ tests/specify_cli/audit/`.
3. Run `pytest tests/specify_cli/audit/ -v`.
4. Address any failure that touches `shape_registry.py` or `detectors.py`; do not introduce unrelated changes.

**Files**: none modified.

**Validation**:
- [ ] mypy clean.
- [ ] ruff clean.
- [ ] All audit tests green.

### T022 — Audit performance gate (NFR-001)

**Purpose**: Confirm the new predicate consult doesn't blow up audit wall-clock. NFR-001 requires audit of a 100-mission tree completes in ≤ 2× the rc13 baseline on the same hardware.

**Steps**:
1. Build a synthetic mission tree with 100 mission directories. Reuse existing fixture helpers if any (look in `tests/specify_cli/audit/` and `tests/conftest.py`); otherwise create a tmp directory with 100 minimal `kitty-specs/<n>-stub/status.events.jsonl` files seeded with a mix of lifecycle + status-transition rows (~50 lines each).
2. Capture the **rc13 baseline** by checking out the `3.2.0rc13` tag (or equivalent commit) in a sibling worktree, running:
   ```bash
   python -c "import time; from specify_cli.audit.detectors import run_audit; \
              t=time.perf_counter(); run_audit(<tmp_tree>); print(time.perf_counter()-t)"
   ```
   Repeat 3 times; record the median.
3. Switch back to this WP's branch. Re-run the same timing 3 times against the patched code; record the median.
4. Assert `median_patched <= 2 * median_baseline`. If the gate fails, profile and investigate. If the gate passes, record both medians in the WP PR description (so reviewers can spot-check).
5. This subtask does **not** need to live in CI as a flaky timing test. Run it locally; capture the numbers in the PR; do not commit a timing-based pytest.

**Files**: none modified.

**Validation**:
- [ ] Baseline + patched medians recorded in PR description.
- [ ] Ratio ≤ 2.0.

## Definition of Done

- [ ] All six subtasks complete; each `[ ]` above checked.
- [ ] No regression on the existing audit test suite.
- [ ] Spec-side requirements FR-001, FR-002, FR-003, FR-009, NFR-001 satisfied.
- [ ] Constraints C-003 (no file split) and C-005 (additive against existing logs) respected — no migration code added.
- [ ] Charter pre-flight items completed: HiC assignment recorded; any pre-existing test failures (if hit) opened as GitHub issues before continuing.

## Reviewer Guidance

- Read the predicate first; confirm both predicates are required (`AND`, not `OR`).
- Verify the comment on `FORBIDDEN_KEYS` in `detectors.py` accurately describes the new scoping.
- Spot-check the regression test for the malformed-row case (`from_lane=..., to_lane=..., event_type=...`) — it must still be flagged.
- Confirm no writer module was modified (`status/lifecycle_events.py`, `invocation/propagator.py`, `dossier/`, `next/_internal_runtime/engine.py`, `retrospective/events.py`).

## Activity Log

- 2026-05-19T09:58:16Z – claude:opus:python-pedro:implementer – shell_pid=52735 – Assigned agent via action command
- 2026-05-19T10:07:07Z – claude:opus:python-pedro:implementer – shell_pid=52735 – WP01 ready: row-family classifier landed; T001-T005 + T022 done; tests pass
- 2026-05-19T10:07:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=57716 – Started review via action command
- 2026-05-19T10:10:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=57716 – Review passed: row-family predicate (AND of aggregate_type=Mission + non-empty event_type) wired into detect_forbidden_keys via live classifier path; 19 new tests pin 6-row contract matrix + edge cases; 192 audit tests pass (1 pre-existing #1134); mypy --strict + ruff clean; NFR-001 perf 1.053x baseline; no writer modules or status.events.jsonl touched (C-003/C-005 respected).
