---
work_package_id: WP05
title: Red-first re-run ordering (persist last-failed nodeids, prioritized recheck)
dependencies:
- WP04
requirement_refs:
- FR-018
- FR-016
- NFR-001
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
history: []
agent_profile: python-pedro
authoritative_surface: scripts/ci/
create_intent:
- scripts/ci/collect_failed_nodeids.py
- tests/ci/test_red_first_ordering.py
execution_mode: code_change
owned_files:
- scripts/ci/collect_failed_nodeids.py
- tests/ci/test_red_first_ordering.py
- .github/workflows/ci-quality.yml
tags: []
tracker_refs: []
---

# WP05 — Red-first re-run ordering

**Capability B** · profile: python-pedro · deps: WP04 · refs: FR-018, FR-016, NFR-001

⚠️ Edits merge-gating `ci-quality.yml` (serial after WP04). Red-first is a **step inside an existing test job**, NOT a new job — so it introduces **no new gate context** and does not need an allowlist entry. Because the file is mutated, keep `test_suite_jobs_gate_blocking.py` + `test_ci_quality_path_filters.py` green (FR-016).

## Objective

On a new push to a PR whose previous run was red, run the previously-failed test nodeids **first**, ahead of the rest of the relevant suite, so a still-broken fix goes red fastest (pairs with the WP04 draft canceller).

## Subtasks

- **T018 — Persist last-failed (`scripts/ci/collect_failed_nodeids.py`).** After a test run, collect failing nodeids (parse `FAILED <nodeid>` / junit if available) into a file; upload as a keyed artifact/cache `flake-lastfailed-<pr-number>`. Pure parse logic unit-tested.
- **T019 — Prioritized recheck (ci-quality.yml `synchronize`, single-pass).** Prefer pytest's native **`--ff` (failed-first)** to avoid double-running: on a new push, restore the persisted `flake-lastfailed-<pr>` into the pytest lastfailed cache (`.pytest_cache/v/cache/lastfailed`), then run the relevant suite once with `--ff` so previously-failed nodeids execute first, the rest after — **no double-run**. Caveat: the repo's parallel command uses `-p no:cacheprovider` (disables the cache) and runners are ephemeral, so seed the cache explicitly and drop `no:cacheprovider` for this job. If `--ff` proves impractical, fall back to a two-pass with `--deselect` of the priority nodeids from the second pass (still no double-run). Missing/renamed nodeids skip harmlessly. No prior red → no-op normal ordering. This is a **step in an existing job**, not a new gate context.
- **T020 — Test (`tests/ci/test_red_first_ordering.py`).** Unit-test the nodeid collection + the ordering selection (given a persisted list + a changed test set, previously-failed present nodeids are ordered first; removed nodeids dropped; empty list → normal order).

## Notes

- Keep the persisted-list read defensive (corrupt/absent → normal order). This is an ergonomics optimization; it must never gate or error the run.
- `ruff`/`mypy --strict` clean; complexity ≤ 15.

## Done when

Collection + ordering logic unit-tested green; ci-quality.yml runs previously-failed nodeids first (single-pass, no double-run) on `synchronize` for a previously-red PR; no-op otherwise; `test_suite_jobs_gate_blocking.py` + `test_ci_quality_path_filters.py` green (file was mutated).
