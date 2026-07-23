---
work_package_id: WP04
title: Single status write-authority (topology-conditional) + empty-second-commit
dependencies:
- WP01
requirement_refs:
- FR-004
- NFR-002
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T015
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- tests/coordination/test_status_write_authority.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/status_transition.py
- tests/coordination/test_status_write_authority.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

(Or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`.) Adopt its directives/tactics; state which you applied.

## Objective

**Single status write-authority** has TWO parts under FR-004:
1. For COORD topology, a status event must commit to the coord worktree — NOT fall back to a primary-uncommitted
   write that leaves readers reading a stale coord log. **Topology-CONDITIONAL, not a delete:** the
   primary-uncommitted fallback is CORRECT for coord-less topologies (`SINGLE_BRANCH`/`LANES`/flat).
2. **Eliminate the empty-second-commit (WP01 causation verdict — this IS the live #2861 blocker).** On the
   MODERN transactional path, `_commit_via_coordination_transaction` already commits the status event to the
   coord worktree; then `commit_workflow_change` attempts a REDUNDANT second commit that finds "nothing to
   commit" → `safe_commit` refuses → the manual review claim fails. ONE write authority = ONE commit: make the
   follow-up workflow commit idempotent (skip it when the transactional emit already committed the transition).

Read `research.md` (Decision E), `contracts/commit-path-contract.md` rows 7-8, `data-model.md`, and the WP01
handoff (the causation verdict + `tests/regression/test_2861_causation_repro.py`).

## Branch Strategy

Planning base + merge target **`remediation/coord-trust-2841`** (coord). Lane c (parallel). You SHARE the
"resolve+target the coord worktree" operation with WP01 — reuse the ONE `CoordinationWorkspace.resolve`
authority (already used at `commit_router.py:~620`); do NOT roll your own resolver.

## Subtasks

### T012 — FR-004 conditionalize the non-transactional fallback (both single + batch)

`status_transition.py:~924` (`emit_status_transition_transactional`, the `_transaction_topology_available`
False arm) AND `:~1028` (`emit_status_transition_batch_transactional`, C25): for COORD topology (a
`coordination_branch` is present) the event MUST materialize/target the coord worktree via
`CoordinationWorkspace.resolve` and commit there — never the primary-uncommitted `_emit.emit_status_transition`
fallback. PRESERVE that fallback for coord-less topologies (`_transaction_topology_available` legitimately
False: `SINGLE_BRANCH`/`LANES`/flat, or no coordination_branch). 

**Campsite (mandatory to stay ≤15):** extract ONE `_emit_via_non_transactional_fallback(...)` so BOTH sites
conditionalize once — do NOT branch-in-place in the C25 batch function.

`tests/coordination/test_status_write_authority.py`: (a) a coord-topology mission → status commits to the
coord worktree (assert via `git show <coord_ref>:…/status.events.jsonl`); (b) **two-sided coord-less coverage
(renata)** — at least ONE topology WITH a `coordination_branch` present but the transactional arm unavailable
(must still NOT force a coord path) AND ONE clearly coord-less (`flat`, no `coordination_branch`); the fallback
branch condition is exercised on BOTH sides — the primary write path is PRESERVED, no coord path forced, no
error. Use the real-git coord fixture for (a).

### T015 — Eliminate the empty-second-commit (the live #2861 blocker) + flip the causation test

Trace `commit_workflow_change` (`workflow_executor.py`): after `_commit_via_coordination_transaction` commits
the transition to the coord worktree, the follow-up commit finds "nothing to commit" and `safe_commit`
refuses. Make it idempotent — the workflow commit must NOT attempt a redundant commit when the transactional
emit already committed the transition (skip / no-op cleanly, do NOT treat "nothing to commit" as a failure on
this path). This coordinates with WP01's work (same `commit_workflow_change` region — WP01 landed first in
lane-a; verify against its `_handle_commit_failure` extraction). **WP04 OWNS flipping
`tests/regression/test_2861_causation_repro.py`'s `exit_code == 1` assertion to `exit_code == 0`** (the manual
review claim now SUCCEEDS) — this is the load-bearing proof that #2861's block is closed. If your fix touches
`workflow_executor.py` (WP01-owned), that is a rationale-recorded out-of-map edit safe via the #1684
dependency-tip merge (WP01 approved-first); prefer keeping the idempotency logic in the `coordination/` seam
you own if feasible.

**Complexity note (pedro):** the "C25" figure for `emit_status_transition_batch_transactional` is a `radon`
number; the CI-gating `ruff C901` count is **11** (4 points of headroom before you touch it). The mandated
`_emit_via_non_transactional_fallback` extraction keeps you well under the binding ≤15. Re-confirm with
`ruff check --select C901` (C-006 — the prompt's number is inherited). If `radon`/Sonar cognitive-complexity
(S3776) still flags the batch fn after extraction (the `BookkeepingTransaction.acquire` nesting drives it),
that's a Sonar-UI PR-callout, NOT a merge blocker — say so in the PR body.

## Definition of Done

- [ ] Coord topology commits status to the coord worktree via `CoordinationWorkspace.resolve` (no primary-uncommitted fork).
- [ ] Coord-less topologies (`SINGLE_BRANCH`/`LANES`/flat) still use the primary write path — regression proves no regression.
- [ ] One `_emit_via_non_transactional_fallback` extracted; both single + batch sites conditionalize once; batch fn stays ≤15.
- [ ] **(T015) The empty-second-commit is eliminated** — `commit_workflow_change` no longer attempts a redundant commit after the transactional emit already committed; the manual review claim SUCCEEDS.
- [ ] **(T015) `tests/regression/test_2861_causation_repro.py` FLIPPED** — its `exit_code == 1` assertion updated to `exit_code == 0` (successful review), proving #2861's block is closed. This is the mission's headline proof.
- [ ] `uv run --extra test ruff check` + `mypy` clean; `uv run --extra test pytest tests/coordination tests/regression/test_2861_causation_repro.py -q` green.

## Reviewer guidance

Verify the coord-less fallback is PRESERVED (a delete would regress flat missions — the top risk); the shared
coord-worktree resolution reuses `CoordinationWorkspace.resolve` (no forked resolver); both single + batch paths fixed.

## Risks

- A blanket delete of the False arm regresses `SINGLE_BRANCH`/`LANES`/flat missions — conditionalize, don't delete.
- Forking a second worktree resolver duplicates the authority (D-001) — reuse `CoordinationWorkspace.resolve`.
