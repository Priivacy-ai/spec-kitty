---
work_package_id: WP01
title: '#2648 — delete the 767 divert, narrow-triple fail-close'
dependencies: []
requirement_refs:
- C-002
- C-004
- C-009
- FR-002
- NFR-001
tracker_refs:
- '2648'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2516512"
shell_pid_created_at: "1784116308.22"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: WP authored after pre-tasks squad — FR-002 re-pinned to the narrow triple (BLOCKER-1); Option B raise, legacy 755/790 arms preserved.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement_writeside.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Close #2648. `_commit_planning_artifacts_transaction` in
`src/specify_cli/cli/commands/implement.py` has a `767` arm (`elif
ProtectionPolicy.resolve(repo_root).is_protected(planning_branch):`) that **silently
diverts a whole dirty-PRIMARY batch to the coordination branch** when `placement_ref is
None` and the mission's own `planning_branch` is protected. Delete that silent divert and
replace it with a **loud fail-close** — `raise PlacementResolutionRequired(...)` with the
**same operator message** as the status-commit half (`_resolve_claim_commit_target`,
`implement_cores.py:608`) — so both halves of a claim agree on that state and no partial
or silent commit to coord occurs.

## Context — READ BEFORE CODING (this is the mission's BLOCKER-1)

- **`placement_ref is None` is NOT unconditionally degenerate.** `_resolve_placement_ref`
  (`implement_cores.py:574-594`) returns `None` on `ActionContextError` OR when
  `artifact_placement is None` — a **deliberate C-004 strangler signal** meaning "keep the
  legacy meta-derived path." The two legacy/flat arms MUST stay green:
  - `755` (`elif not coord_branch:`) — flat/legacy → commit to `planning_branch`.
  - `790` (`else:`) — coord mission with a **non-protected** `planning_branch` →
    partition-aware split (`_partition_files_for_commit`).
- **Three shipped write-side tests drive `placement_ref=None` expecting SUCCESS**:
  `tests/specify_cli/cli/commands/test_implement_writeside.py:192, 218, 251` (the `790`
  partition split and the `755` flat collapse), plus the #2533 regression
  `tests/specify_cli/cli/commands/test_implement.py:283`
  (`TestSoloPrBoundCoordMissionClaimPrecondition`). **An unconditional `None`→raise reds
  all of them and breaks real flat/legacy claims — do NOT do that.**
- **The fail-close condition is the NARROW TRIPLE** — `placement_ref is None` **AND** the
  meta-derived `coord_branch` is truthy **AND** `is_protected(planning_branch)`. That is
  EXACTLY the `767` precondition and EXACTLY where the status half already raises, so both
  halves agree there while the legacy arms are untouched.
- **Boundary (C-002/C-009):** additive; do not restructure unrelated parts of
  `implement.py`; `mission_runtime/*` stays read-only; do NOT reintroduce a silent fallback
  to the default branch (`main`). See `../contracts/partition-authority-and-warning.md` §3
  (authoritative) and `../data-model.md` INV-6/INV-7.

## Subtasks

### T001 — RED repro: narrow-triple currently diverts silently

1. In `test_implement_writeside.py`, use the existing `_seeded_coord_mission` harness with
   `planning_branch="main"` (protected) and `placement_ref=None`, and a genuinely-dirty
   PRIMARY file in `files_to_commit`.
2. Assert the CURRENT (RED-target) behavior: the batch is committed to the **coord** ref
   (capture via the `_fake_bookkeeping_transaction` call list). This documents the silent
   divert that the fix removes.

**Validation**: the assertion captures a coord-destination commit against current code.

### T002 — Baseline: pin the arms that MUST stay green

1. Confirm (run, do not modify) the three existing `placement_ref=None` success cases
   (`test_implement_writeside.py:192/231/285`) and the #2533 regression
   (`test_implement.py:283`) are GREEN before any change. These are the C-004 strangler
   arms + the #2533 guard the fix must not break.

**Validation**: all six are green pre-change (record the baseline in the WP notes).

### T003 — Replace the 767 arm with an explicit fail-close (Option B)

1. In `_commit_planning_artifacts_transaction`, replace the body of the `767` arm
   (`elif ProtectionPolicy.resolve(repo_root).is_protected(planning_branch):`) with:
   `raise PlacementResolutionRequired(<the same message text as
   _resolve_claim_commit_target in implement_cores.py:608-618>)`.
2. No extra empty-batch guard is needed inside this function — the `if not files_to_commit:
   return` short-circuit lives in the **caller** (`_ensure_planning_artifacts_committed_git`,
   ~`:559`), which returns before `_commit_planning_artifacts_transaction` is invoked. Just
   replace the `767` arm body; do not add a redundant guard.
3. Leave the `755` (`not coord_branch`) and `790` (`else` partition split) arms untouched.
4. Do NOT choose "Option A" (delete the arm and let `790` hit BookkeepingTransaction's
   generic `typer.Exit(1)`) — that raises the wrong type/message and fails SC-002.

**Validation**: `ruff` + `mypy --strict` clean; the arm now raises, not commits.

### T004 — Flip RED→GREEN and re-assert the preserved arms

1. Update T001 to assert `pytest.raises(PlacementResolutionRequired)` with the message
   matching the status half.
2. Re-run the T002 baseline (the 3 write-side `None` cases + `TestSoloPrBoundCoordMission…`)
   — all must stay GREEN.

**Validation**: narrow-triple test green (raises); the six preserved tests green.

### T005 — Correct the misleading docstring

1. Rewrite the `_commit_planning_artifacts_transaction` docstring passages that claim the
   `767` arm "falls back to the historical single coordination-branch transaction" (the
   `706-713` block and the `755-766` "genuinely-legacy" narrative) to state the
   narrow-triple fail-close and the preserved `755`/`790` strangler arms.

**Validation**: docstring matches the shipped behavior; no "divert to coord" wording remains.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Execution worktrees are allocated per computed lane from `lanes.json` during
`/spec-kitty.implement`; this WP is the head of **Lane A** (no dependencies).

## Definition of Done

- The `767` silent divert is gone; the narrow-triple state raises `PlacementResolutionRequired`
  with the status-half message (SC-002, FR-002, C-009).
- The three write-side `placement_ref=None` success tests + the #2533 regression stay green
  (INV-7, C-004).
- `ruff` + `mypy --strict` zero new issues (NFR-001).
- Docstring corrected (T005).

## Risks & Reviewer Guidance

- **Highest risk: over-broadening the fail-close to bare `None`.** Reviewer must confirm the
  raise fires ONLY on the narrow triple and that the 3 write-side `None` tests + #2533 stay
  green. This is the whole point of the pre-tasks correction (#2463 None-overload).
- Confirm the message text is byte-identical to `_resolve_claim_commit_target`'s so the two
  halves are indistinguishable to the operator.

## Activity Log

- 2026-07-15T11:21:57Z – claude:sonnet:python-pedro:implementer – shell_pid=2409023 – Assigned agent via action command
- 2026-07-15T11:51:13Z – claude:sonnet:python-pedro:implementer – shell_pid=2409023 – Ready for review: narrow-triple fail-close (Option B); 755/790 arms + 3 write-side tests + #2533 green
- 2026-07-15T11:51:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=2516512 – Started review via action command
- 2026-07-15T12:03:44Z – user – shell_pid=2516512 – Review PASS (reviewer-renata): narrow-triple fail-close correct (raise only in former-767 arm; 755/790 untouched; not on bare None); Option B byte-identical 485-char message; RED-first confirmed; raise on live path re-raised at implement(); ruff+mypy clean; mission_runtime untouched. COLLATERAL test_implement.py re-pins (main->mission/slug) LEGIT stale-placeholder repair (790 arm still stages on coord worktree; intent preserved), flagged as shared/unowned across lane-a.
