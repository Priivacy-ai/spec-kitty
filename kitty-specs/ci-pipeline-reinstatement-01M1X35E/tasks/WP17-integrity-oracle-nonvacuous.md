---
work_package_id: WP17
title: CI-integrity oracle non-vacuity + planted-orphan
dependencies:
- WP07
- WP09
requirement_refs:
- FR-016
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T088
- T089
- T090
- T091
- T092
- T093
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/_ci_integrity_oracle.py
create_intent:
- tests/architectural/_ci_integrity_oracle.py
- tests/architectural/test_ci_integrity_oracle_nonvacuous.py
execution_mode: code_change
owned_files:
- tests/architectural/_ci_integrity_oracle.py
- tests/architectural/test_ci_integrity_oracle_nonvacuous.py
- tests/architectural/_gate_coverage.py
role: implementer
tags: []
tracker_refs:
- '#2967'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (LEAN-SUITE L3), `spec.md`
FR-016 + SC-004 + US8 scenario 2, `contracts/p1-census-oracle.md` §"CI-integrity
oracle", `contracts/router-two-authority.md` §Invariant 4, and the charter §"ATDD-First"
+ SO#5 + DIR-043.

**Cluster gate:** claim after WP07 (router + gate-selection authority) + WP09 (live
shards) are approved/done.

## Objective

Rebuild the **collection-completeness / two-authority integrity oracle** against the
**real on-disk reinstated YAML** so that **no test is selected by zero gates** (SC-004),
with a **non-vacuity floor + planted-orphan negative** (closing the currently-vacuous
oracle), and **fix the zero-producer / inert-slot bare-name false-pass** in
`_gate_coverage.py` (#2967). The oracle proves **wiring**; each gate's **runtime**
execution is evidenced by its own job result (not inferred from the static oracle).

## Subtask guidance

### T088 — Red-first: reproduce the real #2967 bare-name false-pass (SEPARATE first commit)

**Red anchor (binding):** do not anchor on "the oracle is absent" — anchor on
**reproducing the real #2967 bare-name false-pass bug**. As your **first commit**,
author `tests/architectural/test_ci_integrity_oracle_nonvacuous.py` that constructs a
**zero-producer / inert-slot bare name** (a gate name that resolves to no real producer)
and asserts it is **NOT** counted as covered. On base, `_gate_coverage.py` still lets
that bare name silently pass, so the assertion **reds for the right reason** — the
concrete #2967 defect, not a missing symbol. Pair it with the **planted-orphan
negative** (a test wired to **no** group reds the oracle) and the **non-vacuity floor**
(the oracle fails if it evaluates nothing) — the SO#5 anchors. **Lazy-import** the
not-yet-existing oracle helper(s) so the file still *collects* green on base and the red
is the failed behavioral assertion, never a collection/import error.

### T089 — Rebuild the oracle against real on-disk YAML

Author `tests/architectural/_ci_integrity_oracle.py`: parse the **real** reinstated
workflow YAML (via WP07's `gate_selection.py` authority — do NOT re-encode the routing),
build the test→gate selection map, and assert no test is zero-gated. Reuse the single
gate-selection authority (one source — FR-016), not a second parser.

### T090 — Non-vacuity floor

Encode the floor: the oracle fails if it evaluates an empty set (DIR-043) — a vacuous
oracle that "passes" because it checked nothing is the exact defect this closes. The
floor is asserted by T088's negative.

### T091 — Fix the zero-producer bare-name false-pass (#2967)

In `tests/architectural/_gate_coverage.py`, fix the zero-producer / inert-slot bare-name
false-pass: a gate slot with no real producer (a bare name that resolves to nothing)
must NOT count as covered. This is the #2967 root cause — a bare name silently passed.

### T092 — Enumerated must-run gates all wired (SC-004)

Assert the enumerated must-run-on-every-`src`-change gates (terminology, layer-rule,
the arch battery, regen-check, etc.) are all wired in the reinstated topology, and the
two-authority routing model is internally consistent. The set is enumerated in the
topology (SC-004).

### T093 — Runtime-vs-static boundary

Assert (and document) the boundary: the oracle proves **wiring**; each gate's runtime
execution is evidenced by its **own job result** (SC-004), never inferred from the
static oracle. This prevents the oracle from over-claiming runtime green.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP17`.
- Depends on WP07, WP09 — claim after approved/done.
- Commit order: **T088 red-first FIRST**, then T089–T093.

## Definition of Done

- T088 red on base (evidence captured), green on final — the red **reproduces the real
  #2967 bare-name false-pass** (a zero-producer/inert-slot bare name currently passes),
  not merely "the oracle is absent"; the oracle helper is lazy-imported so the file
  collects.
- `_ci_integrity_oracle.py` parses real on-disk YAML via the single gate-selection
  authority (no second parser); a planted-orphan test reds it; a non-vacuity floor
  fails when it evaluates nothing.
- The `_gate_coverage.py` zero-producer bare-name false-pass is fixed (#2967).
- The enumerated must-run gates are all asserted wired (SC-004); runtime-vs-static
  boundary documented.
- **Targeted test surface**: `pytest tests/architectural/test_ci_integrity_oracle_nonvacuous.py tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_gate_selection_authority.py -q`.

## Risks

- **Re-encode temptation**: the oracle must consume WP07's authority, not build a second
  routing parser (that re-opens #2476/#2967) — reviewer confirms single-source.
- **Vacuous rebuild**: rebuilding without the floor recreates the very defect — the
  planted-orphan negative must actually fail.
- **`_gate_coverage.py` blast radius**: this helper is consumed by other arch tests;
  confirm the #2967 fix doesn't red an unrelated consumer (classify via baseline-red
  gotcha).
- **New-file arch battery**: new oracle support + test file trips dead-symbol `__all__`
  / new-test-dir routing — pre-check locally.

## Reviewer guidance

- Confirm T088 red-on-base for the right reason and that the planted-orphan reds the
  rebuilt oracle.
- Confirm the oracle consumes `gate_selection.py` (open it — reject a second parser).
- Confirm the #2967 bare-name false-pass is genuinely fixed (plant a zero-producer slot;
  confirm it no longer passes).
- Confirm the runtime-vs-static boundary is explicit (the oracle does not claim runtime
  green).
