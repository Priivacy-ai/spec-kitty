---
work_package_id: WP17
title: CI gate + coverage guards (quality-gate.needs ⊇ pytest-jobs; Sonar UI-e2e denominator)
dependencies:
- WP16
requirement_refs:
- FR-012
- FR-013
- FR-016
- NFR-002
tracker_refs:
- '2622'
- '2623'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T081
- T082
- T083
- T084
- T085
- T086
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-quality.yml
create_intent:
- tests/architectural/test_suite_jobs_gate_blocking.py
- tests/architectural/test_ui_e2e_coverage_discovered.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_suite_jobs_gate_blocking.py
- tests/architectural/test_ui_e2e_coverage_discovered.py
role: implementer
tags: []
shell_pid: "3546106"
shell_pid_created_at: "1783965155.58"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-012/FR-013 +
Scenario 3, [data-model.md](../data-model.md) E-08/E-09, [plan.md](../plan.md) §IC-11 + §IC-12 + the
"New-guard-file DoD" directive, and the contract
[contracts/quality-gate-needs-containment.md](../contracts/quality-gate-needs-containment.md). This WP is the
**sole owner** of `.github/workflows/ci-quality.yml` (combining the two guards on one file). New-guard-file
DoD applies to both new guard files.

## Objective

Two structural CI guards over `ci-quality.yml` (single-file ownership, IC-11 then IC-12):
1. **FR-012** — assert every `pytest`-invoking job is a member of `quality-gate.needs`, minus a reasoned
   `NON_BLOCKING_ALLOWLIST`; force `slow-tests`/`mutation-testing` to an explicit state.
2. **FR-013** — make the sonarcloud job discover the `ui-e2e.yml`-run `coverage-ui-e2e.xml` (cross-workflow,
   head-SHA-keyed) so UI-e2e dashboard coverage reaches Sonar's denominator, with a wiring guard.

## Context

- Use `_gate_coverage.WorkflowModel` (`tests/architectural/_gate_coverage.py:372`) to parse the workflow —
  derive `pytest_jobs` from the model (a job whose steps' run-cmds match `\bpytest\b`), do NOT hard-code the
  job list, do NOT match `pytest` in comments/strings.
- `slow-tests`/`mutation-testing`/`sonarcloud` are absent from `quality-gate.needs` by convention only.
- `coverage-ui-e2e.xml` (`--cov=src/specify_cli/dashboard`) is produced by `ui-e2e.yml` but never enters
  Sonar's denominator (same-workflow artifact discovery only today). IC-12 is verifiable only post-merge, so
  it MUST be paired with the pre-merge wiring guard.

## Subtask guidance

- **T081 — containment guard (FR-012).** Create `tests/architectural/test_suite_jobs_gate_blocking.py`:
  `pytest_jobs − NON_BLOCKING_ALLOWLIST ⊆ quality_gate.needs`, deriving `pytest_jobs` from
  `WorkflowModel`. Each `NON_BLOCKING_ALLOWLIST` entry carries a why-non-blocking rationale string
  (mirroring the CI_INVISIBLE ledger pattern).
- **T082 — resolve slow/mutation.** Bring `slow-tests` and `mutation-testing` to an explicit state: either
  add them to `quality-gate.needs` in `ci-quality.yml`, or add them to `NON_BLOCKING_ALLOWLIST` with a
  rationale. Never left silently absent.
- **T083 — red-first regression (FR-012).** A regression adds a fake pytest job to the parsed model and
  asserts the guard **fails**.
- **T084 — Sonar cross-workflow discovery (FR-013).** Edit the sonarcloud job in `ci-quality.yml` to
  discover the `ui-e2e.yml`-run `coverage-ui-e2e.xml`, cross-workflow, keyed to the head SHA's latest
  successful run — mirroring the existing `prev_run` fallback shape.
- **T085 — wiring guard (FR-013).** Create `tests/architectural/test_ui_e2e_coverage_discovered.py`
  asserting `coverage-ui-e2e.xml` is a member of the discovered coverage set (so the path cannot silently
  rot).
- **T086 — needs edits + new-guard-file DoD + gates.** Apply any `quality-gate.needs` edits required; then
  register **both** new arch files in `tests/_arch_shard_map.py` (a **recorded out-of-map append** — WP16
  owns that file; append line-disjoint entries, one-line rationale in review) and re-freeze both
  gate-coverage baselines (gc3b `--update-baseline`, gc2b `--freeze-baselines`); residual negates every
  `next_shard`/`arch_shard` marker. `ruff`/`mypy` clean; append tracer rows.

## Branch Strategy

Lane B, last in the serial chain. Branches from WP16's tip (so the shard-registry seam + `_arch_shard_map.py`
edits are already present); merges into `feat/test-suite-friction-remediation`. Because WP16 lands first, the
`_arch_shard_map.py` registration append here is trivially mergeable.

## Definition of Done (non-fakeable — NFR-002)

- [ ] `test_suite_jobs_gate_blocking.py` asserts `pytest_jobs − allowlist ⊆ quality-gate.needs`, deriving
      `pytest_jobs` from the workflow model (not hard-coded).
- [ ] A regression adds a fake pytest job and the guard **fails**.
- [ ] `slow-tests` + `mutation-testing` resolved to an explicit state (gated OR allowlisted-with-rationale).
- [ ] The sonarcloud job discovers `coverage-ui-e2e.xml` cross-workflow (head-SHA-keyed);
      `test_ui_e2e_coverage_discovered.py` asserts the path is in the discovered set.
- [ ] New-guard-file DoD satisfied for BOTH new files: shard-registered (append into WP16's already-present
      `register()` seam — WP16 is upstream serial) + both baselines re-frozen; residual negates every
      `next_shard`/`arch_shard` marker.
- [ ] **Terminal refreeze (WP17 is the Lane-B terminus → authoritative final refreeze):** the terminal gc3b
      (`--update-baseline`) + gc2b (`--freeze-baselines`) refreeze regenerates the baselines capturing **ALL
      THREE** new arch guard files (`test_golden_count_ban.py`, `test_suite_jobs_gate_blocking.py`,
      `test_ui_e2e_coverage_discovered.py`); residual negates every `next_shard`/`arch_shard` marker.
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.
- [ ] **Tracer (FR-016):** append catalog rows for the CI gate-containment + coverage-discovery guards +
      friction log. Record in the PR body that IC-12's real effect is post-merge (the wiring guard is the
      pre-merge proxy).

## Risks

- **Mis-detecting pytest steps** — anchor on the `\bpytest\b` run-command token; do not match comments/strings.
- **Cross-workflow artifact lookup** auth/run-id edge cases — mirror the existing `prev_run` fallback shape;
  IC-12 is verifiable only post-merge, so the wiring guard is the pre-merge safety net.
- **`_arch_shard_map.py` append vs WP16** — WP16 lands first (serial); keep this a line-disjoint append.

## Reviewer guidance

- Confirm `pytest_jobs` is derived from the model (grep the guard for a hard-coded job list → must be none).
- Confirm each allowlist entry carries a rationale and the fake-job regression fails.
- Confirm the PR body notes IC-12's post-merge verification and any residual advisory gate (NFR-006).

## Activity Log

- 2026-07-13T18:38:39Z – claude – shell_pid=3546106 – Both CI guards green (14 passed); gate-coverage+shard 38 passed; regression 85 passed/2 skipped; new-guard DoD done (registered arch_shard_3, refroze gc3b+gc2b); ruff/mypy clean; commit a50ce86bf. Force: lane planning/status-behind only.
- 2026-07-13T18:38:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=3546106 – Review claim
- 2026-07-13T18:44:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=3546106 – APPROVE (reviewer-renata/opus): both guards non-vacuous (fault-injections bite); slow-tests gate-add safe (filter_true=False); sonar cross-workflow wiring producer/consumer names agree; new-guard DoD honest (gc3b +14=new tests, orphan_files=[], gc2b BASELINE_TARGETS exclude architectural); scope=7 files. 21 passed; ruff/mypy clean. Commit a50ce86bf. Note: live Sonar effect verifiable post-merge only (disclosed).
