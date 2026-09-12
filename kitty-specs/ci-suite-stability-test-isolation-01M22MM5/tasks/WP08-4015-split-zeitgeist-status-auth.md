---
work_package_id: WP08
title: '#4015 split: zeitgeist/cross_cutting/status/review/auth timing tests'
dependencies:
- WP05
requirement_refs:
- FR-009
- FR-010
- FR-012
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: 4076913f92e0aec231aa490782294e8798e58fb9
created_at: '2026-09-09T16:53:46.686555+00:00'
subtasks: []
phase: Phase 2 - Lane B split
history:
- at: '2026-09-09T09:08:01Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/status/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/zeitgeist_client/**
- tests/cross_cutting/**
- tests/status/**
- tests/review/**
- tests/auth/**
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read [spec.md](../spec.md) §#4015 + [research.md](../research.md) Decision 3/4. Canonical per-test lists are in commit `1d59ed2ca6`'s body (`git log -1 --format=%B 1d59ed2ca6`) — that is ground truth, do not re-derive a divergent set.

## Objective
Remediate the #4015 timing tests in the owned subsystem(s): SPLIT mixed timing+functional (functional assert stays per-PR unmarked; timing assert → its own \`@pytest.mark.performance\` test using \`tests/_perf_helpers.py::assert_timing_budget\`, collected+green on the nightly lane with the budget value PRESERVED); remediate any vocab-blocked timing-only tests (helper/rename); apply ONLY the deletes pre-approved in WP05's consolidated sign-off. (FR-009, FR-010, FR-012, NFR-003, NFR-004, NFR-005)

## Guidance
- Source of truth for WHICH tests: commit \`1d59ed2ca6\` body, filtered to this WP's owned subsystem(s).
- SPLIT template: copy shared setup → (1) unmarked functional test keeping the functional assert(s) at minimal call count; (2) \`@performance\` test keeping the timing assert via \`assert_timing_budget\`. Never delete a functional assert.
- The #3665 guard (\`test_performance_marker_guard.py\`) must stay green; do NOT widen TIMING_ASSERTION_VOCABULARY.
- Register every NEW/relocated test file in \`tests/_next_shard_map.py\` if it falls under that map's roots (cross-lane coordination — union-resolve at merge).
- Record this WP's coverage-mapping rows in the Activity Log (WP05 format).

## Validation (per-lane .venv; foreground)
- \`PWHEADLESS=1 SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/python -m pytest <owned subsystem test dirs> -q -p no:cacheprovider\` green on the per-PR selection (functional asserts intact).
- Prove each relocated @performance test is COLLECTED BY THE NIGHTLY LANE'S OWN SELECTION (shard-map entry recorded for WP05 + the nightly `-m performance` selection enumerates it) — not merely a hand-listed `-m performance <path>` run (R2: a hand-listed run does not prove nightly collection).
- \`.venv/bin/python -m pytest tests/architectural/test_performance_marker_guard.py -q\` green.
## Definition of Done
- All owned-subsystem mixed tests split (functional per-PR, timing @performance nightly-COLLECTED, budgets preserved); vocab-blocked remediated; only WP05-signed-off deletes applied; guard green; `test_timing_coverage_invariant.py` passes (no functional-assert coverage dropped — R1); mapping rows + new/relocated filenames recorded for WP05 shard-map registration.
## Reviewer guidance
- Verify NO functional assertion moved off per-PR or weakened; verify relocated timing tests are guard-clean + collected nightly; verify any deletion was in WP05's signed-off list.
