---
work_package_id: WP04
title: '#846 — specify/plan auto-commit gates on substantive content'
dependencies: []
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane-based; computed by finalize-tasks. Final merge target is main.
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: claude
history:
- at: '2026-04-28T19:59:16Z'
  actor: planner
  note: Initial work package created from /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
execution_mode: code_change
mission_id: 01KQAJA02YZ2Q7SH5WND713HKA
mission_slug: charter-e2e-827-followups-01KQAJA0
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/missions/_substantive.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/missions/*/command-templates/specify.md
- src/specify_cli/missions/*/command-templates/plan.md
- tests/integration/test_specify_plan_commit_boundary.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile:

```
/ad-hoc-profile-load python-pedro
```

This sets `role=implementer`, scopes editing to the `owned_files` declared above, and applies Python-specialist standards.

## Objective

Gate the auto-commit branches in `setup-plan` (and the analogous specify path) on a deterministic substantive-content check. When the user's spec.md/plan.md is empty, template-only, or insubstantial, do NOT auto-commit a "ready" envelope; emit `phase_complete=false` with a `blocked_reason` so workflow status accurately reflects the incomplete state. Document the boundary in mission templates so future agents understand it.

Per Constraint **C-007**, this WP MUST NOT silently delete or rewrite existing substantive content; it only changes the auto-commit decision boundary and the surfaced workflow state.

## Context

- The current `mission create` flow auto-commits scaffolded `spec.md` and `meta.json`. We observed this concretely while building this very mission: an empty `spec.md` was committed before substantive content was written. That is the bug.
- The auto-commit decision branch lives in `src/specify_cli/cli/commands/agent/mission.py` (see `setup-plan` command and the analogous specify path; both call into a commit helper).
- `mission setup-plan --json` returns a structured payload that downstream tools use to decide if the spec/plan phase is "ready". Today, the payload reports success even when the file is empty.
- Contract for this fix: [`contracts/specify-plan-commit-boundary.md`](../contracts/specify-plan-commit-boundary.md) and [`data-model.md`](../data-model.md) (INV-846-1, INV-846-2, INV-846-3).
- Research decision: see [`research.md`](../research.md) R7 (substantive-content definition) and R8 (gate placement).

## Detailed guidance per subtask

### Subtask T014 — Implement `_is_substantive(file_path, kind)` helper

**Purpose**: Deterministic, cheap gate function used by the auto-commit branches.

**Steps**:

1. Create a new module `src/specify_cli/missions/_substantive.py`.
2. Module structure:
   ```python
   """Substantive-content gate for spec/plan auto-commit (#846)."""
   from __future__ import annotations
   from pathlib import Path
   from typing import Literal
   import functools

   SUBSTANTIVE_DELTA = 256  # bytes; threshold above scaffold size

   Kind = Literal["spec", "plan"]

   @functools.lru_cache(maxsize=None)
   def _canonical_scaffold_bytes(kind: Kind) -> bytes:
       """Return the canonical scaffold bytes for the given artifact kind.

       Reads from the same template the create command uses to scaffold
       new specs/plans, so the gate moves in lockstep with the scaffold.
       """
       # ... implementation: locate the canonical scaffold file in the
       # missions templates tree and read it once, cached.

   def _has_required_sections(body: bytes, kind: Kind) -> bool:
       """Cheap parse: return True iff the file has the minimum required
       sections for that artifact kind.

       - spec: at least one Functional Requirements row with an FR-### ID
       - plan: a non-empty Technical Context section
       """
       # ... implementation: regex/string match against the body.

   def is_substantive(file_path: Path, kind: Kind) -> bool:
       """Return True iff the file is materially beyond scaffold."""
       body = file_path.read_bytes()
       scaffold = _canonical_scaffold_bytes(kind)
       if len(body) - len(scaffold) > SUBSTANTIVE_DELTA:
           return True
       return _has_required_sections(body, kind)
   ```
3. Required-section heuristics (keep tight; do NOT over-parse):
   - **spec**: regex match for a row containing an ID like `FR-\d{3}` followed by content (a non-empty description column). One match is enough.
   - **plan**: presence of a non-template-placeholder `Language/Version` value in the Technical Context section. Detect template placeholders like `[e.g., Python 3.11 ...]` or `[NEEDS CLARIFICATION ...]` as NON-substantive.
4. `mypy --strict` clean.

**Files**: `src/specify_cli/missions/_substantive.py` (new, ~80–120 lines including docstring).

**Validation**:
- [ ] `is_substantive(<empty-scaffold>, "spec")` returns False.
- [ ] `is_substantive(<scaffold + 300 bytes prose>, "spec")` returns True (byte-length branch).
- [ ] `is_substantive(<scaffold + FR-001 row>, "spec")` returns True (section branch).
- [ ] `is_substantive(<scaffold-only plan>, "plan")` returns False.
- [ ] `is_substantive(<plan with populated Language/Version>, "plan")` returns True.

### Subtask T015 — Wire the gate into `mission.py`

**Purpose**: Apply the gate at the auto-commit decision branch in `setup-plan` and the analogous specify path.

**Steps**:

1. Open `src/specify_cli/cli/commands/agent/mission.py`.
2. Locate the auto-commit branches in:
   - The `setup-plan` command (commits the populated `plan.md`).
   - The specify code path (commits the populated `spec.md`).
3. Wrap the commit call:
   ```python
   from specify_cli.missions._substantive import is_substantive

   if is_substantive(spec_path, kind="spec"):
       _safe_commit(...)
       payload["phase_complete"] = True
   else:
       payload["phase_complete"] = False
       payload["blocked_reason"] = (
           "spec content is not substantive yet; agent must populate substantive "
           "requirements before the spec phase can be marked complete. "
           "See kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md."
       )
       # do NOT commit
   ```
4. Apply the same shape to the plan auto-commit, using `kind="plan"`.
5. Ensure the JSON output of `mission setup-plan --json` includes `phase_complete` and `blocked_reason` consistently. If those keys already exist with different semantics, align — the `phase_complete=False / blocked_reason=...` shape is the new contract.
6. Per Constraint C-007: do NOT delete or rewrite existing substantive content. The gate only changes the COMMIT decision; if the file already has content, it stays as the user wrote it.

**Files**: `src/specify_cli/cli/commands/agent/mission.py` (modified, ~30–60 changed lines).

**Validation**:
- [ ] `mission create` followed immediately by `setup-plan` (with no spec content written between) yields `phase_complete=False` and a `blocked_reason` mentioning "substantive content".
- [ ] After the user populates `spec.md` with at least one FR row and re-runs `setup-plan`, the auto-commit fires and `phase_complete=True`.
- [ ] No silent overwrite or deletion of existing content.
- [ ] `mypy --strict` clean.

### Subtask T016 [P] — Update mission templates

**Purpose**: Document the commit boundary in the templates that future agents will read.

**Steps**:

1. Locate command templates under `src/specify_cli/missions/<mission-type>/command-templates/`. There are templates for both `specify.md` and `plan.md` per supported mission type (`software-dev`, `research`, etc.).
2. To each template, add a short "Commit Boundary" subsection (~10–15 lines) explaining:
   - Why the workflow may refuse to auto-commit a scaffold-only file.
   - What "substantive content" means operationally (one FR row for spec, a populated Technical Context for plan; OR > 256 bytes beyond scaffold).
   - How to advance: populate substantive content, re-run the workflow command.
3. Cross-reference [`contracts/specify-plan-commit-boundary.md`](../contracts/specify-plan-commit-boundary.md) so a curious agent can find the canonical contract.
4. Do NOT restructure unrelated parts of the templates.
5. **Important**: per CLAUDE.md, edit the SOURCE templates under `src/specify_cli/missions/`, NOT the agent copies under `.claude/`, `.amazonq/`, etc.

**Files**: `src/specify_cli/missions/<mission-type>/command-templates/specify.md` and `plan.md` (modified, multiple files; ~10–15 lines added per file).

**Validation**:
- [ ] Each touched template has a "Commit Boundary" section.
- [ ] No agent-copy directory was modified.

### Subtask T017 — Author the regression test

**Purpose**: Lock in the gate at the integration level, per FR-015.

**Steps**:

1. Create `tests/integration/test_specify_plan_commit_boundary.py`.
2. Test 1: empty scaffold blocks
   ```
   GIVEN a fresh mission whose spec.md is exactly the empty scaffold from `mission create`
   WHEN setup-plan (or the specify auto-commit path) runs
   THEN no commit is created for the spec/plan
   AND JSON output reports phase_complete=False with a blocked_reason
       containing the phrase "substantive content"
   ```
3. Test 2: populated commits
   ```
   GIVEN a fresh mission whose spec.md has been populated with ≥1 FR row
   WHEN setup-plan runs
   THEN a commit IS created
   AND JSON output reports phase_complete=True
   ```
4. Test 3: byte-length branch
   ```
   GIVEN a fresh mission whose spec.md is the empty scaffold + 300 bytes of arbitrary prose
   WHEN setup-plan runs
   THEN a commit IS created (byte-length branch fires even without an FR table)
   ```
5. Test 4 (optional, for plan side): repeat the above for plan.md → ensures both paths use the gate.
6. Use isolated temp git repos / temp mission scaffolds — do NOT pollute the real `kitty-specs/` tree during tests.
7. Skip with clear reason if the test environment can't create a temp mission.

**Files**: `tests/integration/test_specify_plan_commit_boundary.py` (new, ~180–250 lines).

**Validation**:
- [ ] All test cases pass.
- [ ] Reverting T015's gate makes Test 1 fail (proves the test is meaningful).

### Subtask T018 — Verify the integration filter

**Purpose**: Confirm no collateral regressions.

**Steps**:

1. Run:
   ```bash
   uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q
   ```
2. All filtered tests pass.
3. If any unrelated test fails because it depended on auto-commit firing for an empty scaffold, fix the test's expectations — the new behavior is correct.

**Validation**:
- [ ] Filtered integration suite is green.

## Branch strategy

- **Planning/base branch**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: lane D per the tasks.md plan; assigned by `finalize-tasks`.

## Definition of Done

- [ ] `src/specify_cli/missions/_substantive.py` exists with `is_substantive()`, `_canonical_scaffold_bytes()` (cached), and `_has_required_sections()`.
- [ ] `src/specify_cli/cli/commands/agent/mission.py` gates the specify and setup-plan auto-commit branches on `is_substantive(...)`. Non-substantive cases emit `phase_complete=False` with a `blocked_reason` containing "substantive content"; substantive cases auto-commit and emit `phase_complete=True`.
- [ ] Mission templates under `src/specify_cli/missions/<mission-type>/command-templates/` document the commit boundary.
- [ ] `tests/integration/test_specify_plan_commit_boundary.py` covers the four scenarios above.
- [ ] `uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q` passes.
- [ ] No edits to agent-copy directories (`.claude/`, `.amazonq/`, etc.).
- [ ] `mypy --strict` clean.
- [ ] Only files in this WP's `owned_files` list were modified.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent claude --mission charter-e2e-827-followups-01KQAJA0
```

## Reviewer guidance

- The substantive-content check is OR-logic (byte-length OR section-presence). Pure byte-length OR pure section-presence in the implementation is wrong.
- The required-section heuristic must reject template placeholders (`[e.g., ...]`, `[NEEDS CLARIFICATION ...]`) as NON-substantive — otherwise the gate silently passes scaffold-only content.
- The fix MUST NOT touch agent-copy directories. These are generated.
- Reviewers should verify that `mission create` followed by `setup-plan` (no content written) returns `phase_complete=False` after this WP — currently it returns success.

## Requirement references

- **FR-012** (auto-commit only when substantive).
- **FR-013** (block clearly when not substantive; do not silently auto-commit).
- **FR-014** (workflow state does not falsely advance).
- **FR-015** (regression coverage or workflow docs define the boundary).
- **FR-016** (PR closeout language — informational; this WP doesn't create the PR but the implementer should make sure the WP's commit messages match the FR-016 closeout style at PR time).
- **C-007** (no silent deletion/rewrite of existing content).
- Contributes to **NFR-003** (verification matrix).
