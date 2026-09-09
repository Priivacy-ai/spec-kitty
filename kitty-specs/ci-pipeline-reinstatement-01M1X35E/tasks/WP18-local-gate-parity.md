---
work_package_id: WP18
title: Gate-selection authority local pre-PR parity consumer
dependencies:
- WP07
- WP17
requirement_refs:
- FR-016
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-pipeline-reinstatement-01M1X35E
base_commit: 9e71b602264af2bd319e90ec5d4d56f2abcf3899
created_at: '2026-09-07T16:09:45.338474+00:00'
subtasks:
- T094
- T095
- T096
- T097
- T098
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: scripts/ci/local_gate_parity.py
create_intent:
- scripts/ci/local_gate_parity.py
- tests/architectural/test_local_gate_parity.py
execution_mode: code_change
owned_files:
- scripts/ci/local_gate_parity.py
- tests/architectural/test_local_gate_parity.py
role: implementer
tags: []
tracker_refs:
- '#2476'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (LEAN-SUITE L3 — the local
parity half), `spec.md` FR-016, `contracts/router-two-authority.md` §Invariant 3
(one authority, no second parser), `contracts/p1-census-oracle.md` §"Gate-selection
authority (#2476)", and the charter §"ATDD-First".

**Cluster gate:** claim after WP07 (the gate-selection authority) + WP17 (integrity
oracle) are approved/done.

## Objective

Deliver the **local pre-PR parity consumer** (#2476): a local command that answers
"which gates/shards will CI run for my current diff" by **consuming WP07's single
gate-selection authority** (`scripts/ci/gate_selection.py`) — **not** a second parser.
This gives a developer arch-pole parity locally so a PR is not surprised by a gate that
only fires in CI. **One authority, reused** — the whole point of #2476/FR-016.

## Subtask guidance

### T094 — Red-first: `test_local_gate_parity.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_local_gate_parity.py`
asserting: for a sample diff (a fixture changed-path set), the **local** parity command
selects the **same** gate/shard set as CI routing — both resolved through the single
`gate_selection.py` authority. Run against base: red for the right reason (the local
consumer `local_gate_parity.py` does not yet exist). Assert singularity: the local path
imports the shared authority, there is no second routing map.

### T095 — Author `scripts/ci/local_gate_parity.py`

Create `scripts/ci/local_gate_parity.py`: compute the local changed-path set (e.g.
`git diff --name-only` against the merge base) and call WP07's `gate_selection.py` to
resolve the selected gates/shards. It must **import** the authority — never re-encode
the routing (that re-opens #2476). Keep complexity ≤15.

### T096 — Local command / entrypoint

Wire a runnable entrypoint — a `make` target (e.g. `make ci-parity`) or a small CLI
invocation — that runs the parity check locally and prints the selected gates. Keep it
proportional (DIR-024); reuse existing `scripts/ci/` conventions
(`quality_gate_decision.py`, `check_dangling_deferrals.py`).

### T097 — Assert parity (#2476)

Assert local selection == CI routing for at least: a docs-only diff (0 code shards), a
single-module `src/**` diff (that module's shard + always-on gates), and a
no-group-match `src/**` diff (run-all). This is the concrete #2476 parity proof.

### T098 — Document the local pre-PR workflow

Document the local pre-PR workflow (cross-reference `quickstart.md`): how a developer
runs the parity check before opening a PR to see the arch-pole/gate selection locally.
Record the #2476 resolution for the issue matrix.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP18`.
- Depends on WP07, WP17 — claim after approved/done.
- Commit order: **T094 red-first FIRST**, then T095–T098.

## Definition of Done

- T094 red on base (evidence captured), green on final.
- `local_gate_parity.py` consumes WP07's `gate_selection.py` (single authority, no
  second parser) and a runnable entrypoint exists.
- Parity asserted for docs-only / single-module / unmatched-run-all diffs (#2476).
- Local pre-PR workflow documented (quickstart cross-ref); #2476 recorded.
- **Targeted test surface**: `pytest tests/architectural/test_local_gate_parity.py tests/architectural/test_gate_selection_authority.py -q`.

## Risks

- **Second parser (the #2476 defect itself)**: if the local path re-encodes routing
  instead of importing the authority, it will drift from CI — exactly what #2476 is
  about. Reviewer confirms the import.
- **Ticket assignment (DIR-012)**: assign #2476 to the HiC before/as you begin.
- **Merge-base resolution**: local diff must be against the correct merge base, or the
  parity is computed on the wrong changed set.
- **New-file arch battery**: new `scripts/ci/` symbol + new test file trips dead-symbol
  `__all__` / new-test-dir routing — pre-check locally.

## Reviewer guidance

- Confirm T094 red-on-base for the right reason.
- Open `local_gate_parity.py` and confirm it IMPORTS `gate_selection.py` (reject any
  second routing map).
- Run the local entrypoint on a docs-only and an unmatched-`src` diff; confirm 0-shard
  and run-all match CI.
- Confirm #2476 is recorded and the workflow is documented.
