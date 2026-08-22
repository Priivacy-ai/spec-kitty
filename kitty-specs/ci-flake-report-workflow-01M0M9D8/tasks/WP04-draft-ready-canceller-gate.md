---
work_package_id: WP04
title: Draft fail-fast canceller + ready full-relevant-signal + merge-gate preservation
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
- FR-016
- C-003
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
history: []
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/
create_intent:
- tests/ci/test_draft_ready_ci_contract.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- scripts/ci/quality_gate_decision.py
- tests/ci/test_draft_ready_ci_contract.py
tags: []
tracker_refs: []
---

# WP04 — Draft fail-fast canceller + ready full-relevant-signal + gate preservation

**Capability B** · profile: implementer-ivan · deps: none · refs: FR-009, FR-010, FR-011, FR-012, FR-016, C-003

⚠️ Touches merge-gating `ci-quality.yml`. High blast radius — the guard tests are the contract. Read `scripts/ci/quality_gate_decision.py`, `tests/architectural/test_suite_jobs_gate_blocking.py`, `test_ci_quality_path_filters.py` FIRST.

## Objective

Extend the existing draft/ready model: draft PRs fail-fast via a canceller; ready PRs run full **relevant** signal; the merge-gate contract is preserved.

## Subtasks

- **T013 — Draft canceller (FR-009).** New job `draft-fail-fast-cancel`: `if: failure() && github.event.pull_request.draft == true`, `needs:` the early suites, `permissions: { actions: write }`, runs `gh api -X POST repos/${{github.repository}}/actions/runs/${{github.run_id}}/cancel`. Race with in-flight jobs is accepted.
- **T014 — Ready relevant-signal (FR-010).** For `draft == false`, diff-relevant chained suites carry `if: always() && <relevant-changes>` so a failed upstream does not skip its relevant downstream. Preserve the existing `changes`/path-filter gating so untouched domains stay un-triggered (full = full *relevant* signal). Convert only resource-ordering chains; keep true logical prerequisites.
- **T015 — Gate preservation AUDIT (FR-011/C-003).** `quality_gate_decision.py` **already** consumes each job's `result` (not `conclusion`) — verified: `VALID_RESULTS`/`_coerce_result` read `.get("result")`. So this is an **audit + regression assertion, not a rewrite**: (a) assert the decision step still reads `.result`; (b) audit `ci-quality.yml` for `continue-on-error` on any gating job and forbid it. ⚠️ **Guard constraint**: `test_ci_quality_path_filters.py::_find_result_gated_jobs` forbids any **job-level `if:`** that gates on `needs.<job>.result` (only `consumer-compatibility` is exempt). So `needs.<job>.result` may be read **only inside the decision run-step/payload**, never in a job-level `if:` — do not introduce one.
- **T016 — Allowlist + guard tests (FR-016).** Add `draft-fail-fast-cancel` to `NON_BLOCKING_ALLOWLIST` (`test_suite_jobs_gate_blocking.py`); keep `test_suite_jobs_gate_blocking.py` + `test_ci_quality_path_filters.py` green. The canceller uses `if: failure()` (not `.result`), so it does not trip the result-gate guard.
- **T017 — Contract test (new `tests/ci/test_draft_ready_ci_contract.py`, mark `fast`).** Static assertions on `ci-quality.yml`: canceller present w/ `actions: write` + allowlisted + draft-conditioned (`if: failure()`, not `.result`); ready jobs use `always()`/relevance; **no `continue-on-error` on gating jobs**; `ready_for_review` in triggers (FR-012); the decision **step** (not a job `if:`) references `needs.*.result`.

## Done when

Guard tests + the new contract test green; `mypy`/`ruff` clean; a sandbox draft PR cancels on first failure and the same PR ready runs relevant chains to completion with merge still blocked on a real failure.
