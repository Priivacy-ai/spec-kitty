---
work_package_id: WP03
title: Lane-allocation retry + post-materialize ancestry gate (#3281)
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-007
planning_base_branch: fix/p0-reliability-triad
merge_target_branch: fix/p0-reliability-triad
branch_strategy: Planning artifacts for this mission were generated on fix/p0-reliability-triad. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/p0-reliability-triad unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
history:
- '2026-08-26: authored by tasks flow (carries post-plan squad corrections C-005/C-006)'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/worktree_allocator.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_claim_ancestry_gate.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py
- tests/specify_cli/cli/commands/agent/test_claim_ancestry_gate.py
- tests/lanes/test_worktree_allocator_atomicity.py
- tests/integration/test_wp_integrity_p0_repro.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

This is the heaviest WP and carries architecture-scout + QA corrections. Read `research.md` (WP03 dispositions) and `contracts/behavioral-contracts.md` (C-WP03) before writing code. Coordinate with robertDouglass (assignee) and the #3432 (closed) compute-side behavior.

## Objective

Three coupled defects on the lane-allocation path (#3281):
1. **Retry short-circuit** — `ensure_workspace_materialized` early-returns on `workspace.exists`, so a retry after a planning-commit merge conflict never re-enters the allocator's idempotent self-heal (planning-commit + dependency-tip merges). Dependency propagation is skipped.
2. **Non-atomic fresh-path** — a conflicting `_merge_recorded_planning_commit` leaves a registered worktree behind.
3. **Ancestry-blind claim** — the claim gate keys only on dependency status-lane, so a WP can be `claimed` against a lane missing its dependencies' code.

**Critical design constraints from the post-plan squad (do not deviate):**
- **C-005 (seam)**: the ancestry check runs **POST-materialize** (after self-heal re-runs the merges), keyed on the **merged** tip, at a seam BOTH the CLI (`workflow.py`) and `orchestrator_api/commands.py` claim paths cross. It must **never** run at the pre-materialize status-lane gate (`workflow.py:1263`) — doing so evaluates ancestry against a pre-merge HEAD and **deadlocks legitimately-approved same-mission dependencies**. On failure, route back into self-heal; hard-refuse only if self-heal cannot establish ancestry.
- **C-006 (invariant)**: the exists-branch re-entry uses a **dedicated idempotent self-heal**, NOT a break of the landed #1832/#1833 single-resolution invariant (`test_implement_single_resolution.py` asserts `_create`/re-resolution does not run when the workspace exists). Update that test's semantics with an explicit rationale, do not silently invert it.
- FR-005 and FR-007 **land together** (a gate without self-heal is a dead-end retry).

## Branch Strategy
- Planning base / merge target: `fix/p0-reliability-triad`. Enter the lane via `spec-kitty agent action implement WP03 --agent claude`.

## Subtasks

### T008 — RED: retry re-enters self-heal (+ invariant reconciliation)
- In `tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py`: add a RED test where a leftover lane worktree `exists` but lacks the recorded planning SHA / an approved dependency tip → `ensure_workspace_materialized` must re-enter the idempotent self-heal (assert the reuse-path merges run), not early-return.
- Reconcile `test_already_materialized_workspace_is_consumed_without_re_resolution` (#1832) and `test_husk_workspace_is_blocked_not_recreated` (#1833): the "no re-resolution when exists" invariant becomes "no re-resolution when exists **and ancestry is already correct**; stale exists → idempotent self-heal". Update with a rationale comment referencing #3281/C-006.

### T009 — exists-branch decision tree
- In `ensure_workspace_materialized` (`workflow_executor.py`), replace the bare `if workspace.exists: return` with an explicit tree: ancestry-correct → no-op resume (preserve Acceptance Scenario 4 and the `is_worktree_context` resume guard); stale → invoke a dedicated idempotent self-heal that re-runs `_merge_recorded_planning_commit` + `_merge_dependency_lane_tips` (needs main-repo context, not the worktree cwd).

### T010 — Atomic fresh-path allocation (FR-006, scoped)
- In `worktree_allocator.py`, on a `_merge_recorded_planning_commit` raise during **fresh-path** allocation, `git worktree remove` the just-created worktree so none remains registered. The merge helpers already `git merge --abort` (tree is clean, not conflicted) — do NOT build heavy rollback; a targeted remove is enough.
- Add a focused test to `tests/lanes/test_worktree_allocator_atomicity.py` (mirrors the #1915 dependency-tip pattern): conflicting `planning_commit_sha` fails closed AND leaves no registered worktree.

### T011 — POST-materialize ancestry predicate
- Implement one shared ancestry predicate: recorded planning SHA + every approved dependency lane tip are git ancestors of workspace HEAD, evaluated AFTER self-heal. On failure, route back into self-heal; hard-refuse (Exit 1) only if ancestry still cannot be established.

### T012 — Both-paths seam (C-005 parity)
- Place the ancestry assertion where BOTH claim paths cross it: the CLI path (`workflow.py`, between `_ensure_workspace_materialized` at :1297 and claim emission) AND `orchestrator_api/commands.py` (its own `planned→claimed→in_progress` composite at ~:973/:1042/:1377). Prefer a shared claim-guard/primitive so `orchestrator_api` is not left ancestry-blind. If a fully shared seam is too large for this release, wire the same predicate into both and record the duplication as a tracked follow-up (do not leave orchestrator_api blind).

### T013 — Focused tests + parity + lint
- New `tests/specify_cli/cli/commands/agent/test_claim_ancestry_gate.py`: focused unit proving the ancestry refusal at the post-materialize seam (FR-007), AND that an approved same-mission dependency does NOT deadlock (regression guard for the C-005 hazard).
- `tests/integration/test_wp_integrity_p0_repro.py`: end-to-end retry-then-claim ancestry assertion as backup (do not overload it as the sole proof; it currently hosts a #3371 lanes.json test).
- ruff + mypy clean; every touched function complexity ≤15; FR-005+FR-007 in the same lane.

## Campsite / complexity discipline (post-tasks Sonar census — all in owned files)

- **`transition` (`orchestrator_api/commands.py:1294`) is at complexity 14** — one branch from the C901 ceiling. Before adding the ancestry gate there: peel the near-identical policy-parse blocks (`:1331-1336` / `:1339-1344`, also in `start_implementation:1050-1054`) into a `_parse_policy_or_fail(cmd, policy)` helper. Then add the gate via the **shared predicate helper** with an early-return for non-claim lanes, so the `transition` call site gains 0–1 branches and stays ≤15.
- **Shared ancestry predicate, not three inline gates**: T012's three call sites (`workflow.py` CLI seam, `start_implementation`, `transition`) must call ONE predicate helper (natural home: `implement_support.py`, owned) — this is both the whack-a-field guard and what keeps all three enclosing functions ≤15.
- **Extract the T009 stale self-heal** (`_merge_recorded_planning_commit` + `_merge_dependency_lane_tips` with main-repo context) into a dedicated helper so `ensure_workspace_materialized` (currently 7) stays flat and T008/T013 get a directly-testable unit.
- **T010 removal** goes in as a `_remove_lane_worktree(...)` sibling helper in `worktree_allocator.py` (matching the module's `_create_lane_worktree`/`_recover_lane_worktree` shape), NOT a 15th inline `subprocess.run`.
- Do NOT broadly refactor the 14 sibling `subprocess.run` blocks — out of scope.

## Definition of Done
- All RED tests (T008, T010, T013) fail before, pass after.
- `transition` and every touched function stay ≤15 (verify with `ruff check`).
- #1832/#1833 invariant test updated with rationale (not silently inverted).
- Ancestry check is post-materialize and enforced on BOTH claim paths (or orchestrator_api parity tracked with rationale).
- No approved same-mission dependency deadlocks (explicit regression test).
- ruff + mypy clean; complexity ≤15.

## Risks / Reviewer guidance
- **Deadlock hazard**: if the ancestry check runs pre-materialize or keys on the live (unmerged) tip, approved same-mission chains deadlock — reviewer verifies the seam is post-materialize and self-heal-coupled.
- **Boundary leak**: reviewer verifies `orchestrator_api` is not left ancestry-blind.
- Coordinate the fresh-path allocation reshape with #2570 friction #1 (allocator serialization) so a later fix doesn't collide.
