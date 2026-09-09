---
work_package_id: WP13
title: Nightly full-mode — expensive cadence + interpreter lane + mis-mark guard
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP09
requirement_refs:
- FR-020
- FR-021
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T066
- T067
- T068
- T069
- T070
- T071
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-nightly.yml
create_intent:
- .github/workflows/ci-nightly.yml
- tests/architectural/test_performance_marker_guard.py
execution_mode: code_change
owned_files:
- .github/workflows/ci-nightly.yml
- tests/architectural/test_performance_marker_guard.py
role: implementer
tags: []
tracker_refs:
- '#3595'
- '#3665'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T6), `spec.md`
US9 + FR-020/FR-021 + SC-011, and the charter §"ATDD-First". Note FR-021: the nightly
lane is **in-mission**; the full above-3.12 burn-down is a linked follow-up (#3189) —
**not** claimed here.

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP09 (module shards) are
approved/done.

## Objective

The **full-mode nightly** workflow: run-all-regardless (`if: always()`), the
**expensive-test cadence** (performance + heavy/e2e tests run on the nightly schedule
and manual dispatch **only**, never on the per-PR blocking path — #3595), and the
**interpreter matrix** lane above Python 3.12 up to the supported ceiling (FR-021,
nightly-only). Plus the **mis-mark guard** (#3665): flag `@pytest.mark.performance`
tests carrying non-timing (functional) assertions, so functional coverage cannot
silently leave the PR path.

## Subtask guidance

### T066 — Red-first: `test_performance_marker_guard.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_performance_marker_guard.py`
that plants a `@pytest.mark.performance` test carrying a **functional** (non-timing)
assertion and asserts the guard **flags** it (a performance-marked test may assert
timing/budget only; a functional assertion under that marker is a mis-mark). Run
against base: red for the right reason (guard absent). This is #3665.
**Collection-red lazy-load hygiene:** any import of a not-yet-existing module/helper is
lazy/in-test so the file still *collects* green on base — the red is a failed behavioral
assertion, never a collection/import error.

### T067 — Author `ci-nightly.yml` (full-mode + expensive cadence)

Create `.github/workflows/ci-nightly.yml`: `on: schedule` (nightly) +
`workflow_dispatch`; full-mode `fail-fast: false` + `if: always()` so every job runs
and reports the complete failure set; include the performance + heavy/e2e jobs (the
dedicated performance-test workflow home — #3595). SHA-pin all actions. **Declare
`workflow_dispatch`; honor the `mode` input** — this is the full-mode lane, so it runs
run-all (`fail-fast: false` + `if: always()`, no PR fail-fast short-circuit) per
FR-018/FR-019; the mode-conditioned behavior lives in this owned workflow file, verified
by WP11's `test_dual_mode_contract`.

### T068 — Interpreter matrix lane (FR-021)

Add a nightly pytest lane running above Python 3.12 up to the supported ceiling, so
interpreter-divergence defects are visible instead of escaping CI. Keep it **off the
per-PR path** (latency protection). Scope: the nightly lane only — do NOT attempt the
full above-3.12 burn-down (#3189 is a deferred follow-up, not in this mission's
verdict scope).

### T069 — Assert PR-path exclusion (SC-011)

Assert (in the marker guard test or a sibling assertion) that performance / heavy-e2e /
interpreter jobs are **not** on the per-PR blocking path — a per-PR run executes 0 of
them (SC-011). They live only in `ci-nightly.yml` + manual dispatch.

### T070 — Mis-mark guard (functional coverage can't leave the PR path)

Complete the #3665 guard: a functional test wrongly marked `@performance` (which would
push it to the nightly-only cadence and off the PR path) is flagged so functional
coverage cannot silently leave the per-PR gate. Enumerate the timing-only assertion
vocabulary the guard permits under the marker.

### T071 — Register `introduced` row + close tickets

Ensure `ci-nightly.yml` has its `introduced` row (coordinated with WP01 — do NOT edit
WP01's owned files; WP01 pre-registers). Record the #3595 (perf workflow) and #3665
(mis-mark guard) resolutions for the issue matrix.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP13`.
- Depends on all FOUNDATION + WP09 — claim after approved/done.
- Commit order: **T066 red-first FIRST**, then T067–T071.

## Definition of Done

- T066 red on base (evidence captured), green on final.
- `ci-nightly.yml` runs full-mode (`if: always()`), houses performance/heavy-e2e +
  the >3.12 interpreter lane, on schedule + dispatch, off the per-PR path; SHA-pinned.
- `test_performance_marker_guard.py` flags a mis-marked functional `@performance` test.
- SC-011 asserted (per-PR run executes 0 perf/e2e/interpreter jobs).
- `ci-nightly.yml` declares `workflow_dispatch` and honors the `mode` input (full-mode
  run-all `if: always()`, no PR fail-fast short-circuit) per FR-018/FR-019 — verified by
  WP11's `test_dual_mode_contract`.
- `introduced` row present (via WP01 coordination); #3595/#3665 recorded.
- **Targeted test surface**: `pytest tests/architectural/test_performance_marker_guard.py -q`
  plus `pytest tests/architectural/test_marker_job_completeness.py tests/architectural/test_fast_tier_marker_completeness.py -q` (marker-topology neighbours).

## Risks

- **Ticket assignment (DIR-012)**: assign #3595 + #3665 to the HiC before/as you begin.
- **#3189 scope creep**: the full above-3.12 burn-down is NOT in scope — land only the
  nightly lane (FR-021). Do not claim #3189.
- **Marker-completeness gates**: adding a marker guard interacts with the existing
  marker-completeness tests (`test_marker_job_completeness`, `test_fast_tier_marker_completeness`)
  — run them; a new marked test needs a job home.
- **Governance-map lockstep**: `introduced` row is WP01-owned — coordinate, don't
  cross-edit.

## Reviewer guidance

- Confirm T066 red-on-base for the right reason.
- Confirm the interpreter lane and perf/e2e are nightly-only (SC-011) — feed a PR-mode
  selection and confirm 0 such jobs.
- Confirm the mis-mark guard actually flags a planted functional `@performance` test.
- Confirm #3189 was NOT claimed.
