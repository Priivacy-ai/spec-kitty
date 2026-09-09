---
work_package_id: WP06
title: Fix-before-wiring + early strict-xfail/env-leak hygiene
dependencies: []
requirement_refs:
- FR-015
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/conftest.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/review/test_transition_gate_parity.py
- tests/specify_cli/cli/commands/agent/test_sc6_planning_placement_e2e.py
- tests/architectural/test_egress_consent_boundary.py
- tests/specify_cli/cli/commands/test_init_integration.py
- tests/agent/test_context_validation_unit.py
- tests/docs/test_check_cli_reference_freshness.py
- tests/conftest.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (FOUNDATION F5 —
fix-before-wiring half), `spec.md` FR-015 + US7 scenario 4, and the charter
§"ATDD-First" + DIR-034 (drive the stable entry point).

## Objective

CI greens/reds must reflect **real state**, not scaffold drift. Two hazards must be
resolved **before** these tests enter a gated shard (FR-015):

1. **Active `xfail(strict=True)` landmines** — a strict-xfail that silently starts
   passing (xpass) reds `strict=True`; each must be re-validated (fix the underlying
   behavior, or convert the marker to reflect true state).
2. **Env-leak tests** — order-dependent tests that pass under `make test-fast`'s
   directory order but red under a different shard order (spec US7 scenario 4). These
   must be made order-independent so they don't red **only in CI**.

This WP is decoupled (no dependencies) and should land early in FOUNDATION so the
TOPOLOGY shards are assembled on clean, order-independent tests.

## Subtask guidance

### T028 — Red-first: re-validate the strict-xfail landmines (SEPARATE first commit)

As your **first commit**, add a behavior assertion (or run-and-capture harness) that
pins the CURRENT strict-xfail state of the named landmines and goes red where the
marker no longer matches reality (an xpass, or an xfail masking a now-fixable bug).
The observable precondition — "these markers do not reflect real state" — is captured
first. Run against base, capture evidence. Confirm each landmine's current disposition
before touching it.

### T029 — Resolve transition-gate-parity + sc6-planning-placement strict-xfail

For `tests/review/test_transition_gate_parity.py` and
`tests/specify_cli/cli/commands/agent/test_sc6_planning_placement_e2e.py`: determine
whether the strict-xfail masks a real bug (fix it at the stable entry point, drop the
marker) or reflects an intended gap (convert to a plain assertion / documented skip
with rationale). Do not leave a strict-xfail that will flip to xpass in a shard.

### T030 — Resolve egress-consent-boundary + init-integration strict-xfail

Same treatment for `tests/architectural/test_egress_consent_boundary.py` and
`tests/specify_cli/cli/commands/test_init_integration.py`. Each ends as a truthful,
non-landmine test.

### T031 — Fix env-leaker `test_context_validation_unit.py`

`tests/agent/test_context_validation_unit.py` leaks environment state across order.
Make it order-independent: isolate the env it reads/writes (fixture-scoped
monkeypatch, explicit setup/teardown), so it passes under any shard order — not only
`make test-fast`'s directory order.

### T032 — Fix env-leaker `test_check_cli_reference_freshness.py`

Same for `tests/docs/test_check_cli_reference_freshness.py` — isolate its env/cwd
dependence so shard order cannot red it.

### T033 — Extend `tests/conftest.py` env-isolation

Extend the shared `tests/conftest.py` env-isolation (building on the existing
per-worker HOME/XDG isolation, WP04 testing infra) so that the class of order-dependent
env leaks these two exposed cannot red **only in CI**. Keep the change proportional
(DIR-024) — a targeted isolation fixture, not a broad conftest rewrite.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP06`.
- No dependencies — land early in FOUNDATION.
- Commit order: **T028 red-first FIRST**, then T029–T033.

## Definition of Done

- T028 red on base (evidence captured), green on final.
- Every named strict-xfail landmine is resolved (fixed or truthfully converted) — no
  remaining `xfail(strict=True)` that will flip to xpass in a shard.
- Both env-leakers pass under a **reversed / randomized** shard order (demonstrate with
  `pytest -p no:randomly`-off or `--reverse`-style ordering, or an explicit
  cross-order run).
- `tests/conftest.py` isolation extended, proportional and behavior-preserving for
  passing tests.
- **Targeted test surface**: the 6 owned test files run together AND in reversed order
  (prove order-independence), e.g. `pytest tests/agent/test_context_validation_unit.py tests/docs/test_check_cli_reference_freshness.py tests/review/test_transition_gate_parity.py tests/architectural/test_egress_consent_boundary.py tests/specify_cli/cli/commands/test_init_integration.py tests/specify_cli/cli/commands/agent/test_sc6_planning_placement_e2e.py -q` plus a cross-order run.

## Risks

- **Conftest blast radius**: `tests/conftest.py` is repo-wide; an over-broad isolation
  change can perturb unrelated tests. Keep it a narrowly-scoped fixture; run a broad
  smoke locally and classify any new red via the baseline-red gotcha (CLAUDE.md).
- **xfail→fix scope creep**: fixing the underlying bug may reach `src/**` outside
  owned_files. If so, coordinate with the orchestrator (do not silently edit outside
  the partition); a pure marker-conversion stays in the owned test file.
- **New test file marker gate** (memory): if you add a new test file it needs a marker;
  here you edit existing files, so watch marker-baseline node-id shifts from any
  renamed nodes — do a documented 1-for-1 swap if a baseline reds.

## Reviewer guidance

- Confirm T028 red-on-base captured the real marker-drift, not a collection error.
- Independently run the two env-leakers in reversed order to confirm order-independence.
- Confirm no strict-xfail landmine survives; each conversion carries a rationale.
- Confirm the conftest change is proportional (DIR-024) and doesn't green-wash a real
  failure.
