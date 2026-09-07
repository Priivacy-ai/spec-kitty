---
work_package_id: WP15
title: P1 machine proofs (planted dead-code/retired-import + allowlist preservation)
dependencies:
- WP02
- WP05
- WP09
requirement_refs:
- C-006
- FR-013
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T077
- T078
- T079
- T080
- T081
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_p1_planted_regression.py
create_intent:
- tests/architectural/test_p1_planted_regression.py
execution_mode: code_change
owned_files:
- tests/architectural/test_p1_planted_regression.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (LEAN-SUITE L1), `spec.md`
FR-013 + C-006 + SC-005 + US7 scenario 2, `contracts/p1-census-oracle.md`, and the
charter §"ATDD-First" + SO#5 (non-vacuous gates) + DIR-043 (close defect class by
construction).

**Cluster gate:** claim after WP02 (census), WP05 (scrub), WP09 (live shards) are
approved/done.

## Objective

Prove — by **planted negatives that actually fail** — that P1 is enforced by
construction, not by a prose promise:

- The **exclusion gate fires**: a planted dead-code shard / retired-import is caught
  (the exclusion is real, not aspirational).
- The **enforcement allowlists still fire**: a planted retired-import / dead-symbol
  regression is still red by `test_no_retired_subsystems` / `test_no_dead_symbols`
  (these stay always-on — C-006).
- **Allowlist preservation**: the P1/P2 demotion (WP16) did NOT weaken the enforcement
  allowlists.
- **Denominator integrity**: a census-`dead` behavioral test never contributes to the
  coverage denominator (SC-005 / NFR-006).

## Subtask guidance

### T077 — Red-first: `test_p1_planted_regression.py` as an AUTOMATED self-mutation (SEPARATE first commit)

**Red-first reframe (binding):** this WP depends on WP02/WP05/WP09, which have already
built the exclusion gate on this WP's base — so a plain "plant dead-code → assert the
exclusion fires" is **GREEN on base**, not red, and is a co-landing tautology. Anchor
the C-011 red-first instead as an **automated self-mutation test**: the test
programmatically **removes/neutralizes the exclusion guard** (in-process, restored in a
fixture teardown — never a committed source edit) and asserts that with the guard gone
the planted dead-code shard / retired-import is **no longer excluded** (the assertion
reds). As your **first commit**, author
`tests/architectural/test_p1_planted_regression.py` with this self-mutation harness and
capture the evidence that the mutated (guard-absent) path reds while the intact path is
green. This is the genuinely-can-FAIL proof the anti-laziness pass targets — the failure
is machine-driven by the harness, not a transient base state.

### T078 — Planted retired-import negative

Add a case: a planted retired-import (sync/saas/delivery/emit) is still red by
`test_no_retired_subsystems`. Prove the always-on allowlist catches it independently of
the exclusion gate.

### T079 — Planted dead-symbol negative

Add a case: a planted dead symbol is still red by `test_no_dead_symbols`. The
enforcement allowlist stays always-on.

### T080 — Allowlist-preservation test

Assert the enforcement allowlists (`test_no_dead_symbols`/`test_no_dead_modules`/
`test_no_retired_subsystems`) are **unchanged in behavior** by the P1/P2 demotion —
cross-reference the WP16 committed membership (E4): every `enforcement-allowlist`
member is still on the blocking gate. This is the guard against a demotion accidentally
gutting the gates P1 depends on.

### T081 — Denominator integrity

Assert a census-`dead` behavioral test never enters the coverage denominator (SC-005 /
NFR-006) — a green run's coverage number is not inflated by dead code. Consume the WP02
census + WP10 aggregation contract.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP15`.
- Depends on WP02, WP05, WP09 — claim after approved/done.
- Commit order: **T077 red-first FIRST**, then T078–T081.

## Definition of Done

- T077's **automated self-mutation** harness reds when it programmatically neutralizes
  the exclusion guard and is green with the guard intact (evidence captured) — the C-011
  anchor is the self-mutation, NOT a base-red plant-and-assert (which is green on this
  WP's deps-built base).
- Each planted negative (dead-code-shard exclusion, retired-import allowlist,
  dead-symbol allowlist) **actually fails** when its guard is removed — proven by the
  automated in-process guard-removal, not only a manual local demonstration.
- Allowlist-preservation asserted against the WP16 membership; denominator integrity
  asserted.
- **Targeted test surface**: `pytest tests/architectural/test_p1_planted_regression.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py -q`.

## Risks

- **Vacuous proof (top squad-flagged risk)**: a planted-negative that cannot actually
  fail is worthless. The reviewer must confirm each negative reds when its guard is
  removed — this is the non-fakeability bar.
- **Membership dependency**: T080 reads the WP16 membership; if WP16 lands after, assert
  against the committed file and coordinate ordering (WP16 is LEAN-SUITE, parallel).
- **New-file arch battery**: new test file trips new-test-dir routing / shard-map — the
  test must itself be on a gate (it is an always-on arch test).

## Reviewer guidance

- Independently remove each guard locally and confirm the corresponding planted negative
  reds — do not accept the green-on-final alone.
- Confirm T077's C-011 anchor is an **automated self-mutation** (the harness itself
  neutralizes the guard and reds), NOT a base-red plant-and-assert — the latter is green
  on this WP's deps-built base and would be a tautology.
- Confirm the allowlist-preservation test references the committed E4 membership, not a
  hand-copy.
