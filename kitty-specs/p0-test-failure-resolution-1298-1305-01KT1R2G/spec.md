# Spec: P0 Test Failure Resolution — Release Blockers 1298-1305

**Mission ID**: 01KT1R2GZRSH1RVG4JJ1VNFC6A  
**Mission slug**: p0-test-failure-resolution-1298-1305-01KT1R2G  
**Mission type**: software-dev  
**Target branch**: main  
**Created**: 2026-06-01  

---

## Overview

217+ pre-existing test failures were discovered and reported per DIR-013 during mission
`test-stabilization-and-debt-pass-01KSF9HJ` (WP04 closeout). These failures were triaged
into root-cause clusters and four residual P0 clusters remain unresolved, each tracked as a
release blocker for the 3.2.0 release. This mission fixes all still-reproducing clusters on
`main` with minimal, issue-scoped changes and adds regression coverage so the 3.2.0 baseline
is clean.

**Tracked issues**: #1298 (baseline tracking), #1301, #1303, #1304, #1305.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The test suite is run on the current `main` HEAD before any fix is applied, and the result — commit SHA, pass/fail/skip counts, and failure cluster grouping — is recorded as the refreshed baseline. | Proposed |
| FR-002 | Each of the four P0 issue clusters (#1301, #1303, #1304, #1305) is verified to still reproduce on the refreshed baseline before a fix is developed; issues that no longer reproduce are recorded as stale and excluded from fix scope. | Proposed |
| FR-003 | The shared-package/events drift cluster (#1301) is resolved: `spec_kitty_events` resolves to the version pinned in `uv.lock`; the sync lifecycle tests (`test_lifecycle_readiness`, `test_daemon_intent_gate`, `test_origin_integration`) pass; the vendored events tree no longer exists on disk; and contract fixture payloads (`WPCreated`) include the required `actor` and `wp_title` fields. | Proposed |
| FR-004 | The `next` CLI exit-code regression cluster (#1305) is resolved: the `next` command returns exit code `0` in terminal and successful-advance scenarios, `decide_next` mocks are correctly invoked, and all four affected tests (`test_blocked_result_exit_code`, `test_terminal_state_exit_code_zero`, `test_advancing_mode_with_result_…`, `test_result_success_calls_decide_not_query`) pass. | Proposed |
| FR-005 | The doctrine/glossary anchor drift cluster (#1304) is resolved: glossary contexts contain anchors `doctrine-pack` and `platform-darwin--platform-linux`; the `five-paradigm-parallel-debugging` tactic schema is valid and all its references resolve; all four affected doctrine tests pass. | Proposed |
| FR-006 | The charter synthesizer non-determinism cluster (#1303) is resolved: synthesizer manifest hashes are stable across repeated runs; direct write primitives are gated behind `path_guard.py`; chokepoint coverage is present; all five affected charter synthesizer tests pass. | Proposed |
| FR-007 | For each resolved cluster, at least one regression test is added or updated to prevent silent reintroduction of the same root cause. | Proposed |
| FR-008 | After all fixes land, a final targeted test run is executed for each affected test module and the results are recorded as the post-fix verification. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage for any newly added or modified source code meets the project minimum. | ≥ 90% line coverage for new code paths | Proposed |
| NFR-002 | Static type checking passes with no new errors introduced by any fix. | `mypy --strict` reports zero additional errors vs. the pre-fix baseline | Proposed |
| NFR-003 | Each fix is minimal and issue-scoped — no unrequested refactoring, cleanup, or feature additions are bundled. | Each changed file is traceable to exactly one of FR-003..FR-006 | Proposed |
| NFR-004 | The broader test suite is no worse after all fixes than the refreshed baseline recorded in FR-001. | Net failure count is equal to or lower than the FR-001 baseline; no previously passing tests are newly broken | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | All work is performed within the spec-kitty checkout at the designated workspace path. The `spec-kitty-saas` and `spec-kitty-tracker` repositories are not touched. | Proposed |
| C-002 | GitHub issues #1298, #1301, #1303, #1304, and #1305 are not closed or updated unless the current evidence on `main` concretely justifies the update. | Proposed |
| C-003 | The baseline refresh (FR-001/FR-002) must complete and be reviewed before any fix work begins; no fix may be applied speculatively before its issue is confirmed to still reproduce. | Proposed |
| C-004 | Fixes use focused, targeted test runs to reproduce and verify each cluster before running the broader suite. | Proposed |

---

## User Scenarios & Testing

### Scenario 1 — Baseline refresh gates all fix work

A release engineer on `main` runs the full test suite (`PWHEADLESS=1 pytest tests/ -q --tb=no -p no:cacheprovider`) and captures the result. The commit SHA, summary counts, and failure clusters are compared against the #1298 baseline (217 failures on `4edf74472`). The outcome determines which of #1301/#1303/#1304/#1305 are still live and which, if any, have been resolved by intervening commits.

**Expected**: A documented current baseline exists before any fix work begins.

### Scenario 2 — Shared-package events drift (#1301) fix verified

A developer runs `pytest tests/sync/ tests/contract/ -q` before the fix and observes failures in `test_events.py`, `test_lifecycle_readiness.py`, `test_daemon_intent_gate.py`, `test_origin_integration.py`, `test_handoff_fixtures.py`, `test_packaging_no_vendored_events.py`. After the fix, the same command reports zero failures in these modules.

**Expected**: The events package resolves to the pinned version; no vendored copy exists; contract payloads are complete.

### Scenario 3 — `next` CLI exit-code fix verified (#1305)

A developer runs `pytest tests/next/ -q` and sees four failures with `assert 1 == 0` patterns. After the fix, the same command reports zero failures, and mocked `decide_next` calls are verified to have been invoked.

**Expected**: `next` returns the correct exit code in all tested scenarios.

### Scenario 4 — Doctrine/glossary anchor fix verified (#1304)

A developer runs `pytest tests/doctrine/ -q` and observes two link-integrity failures (missing anchors) and two tactic-compliance failures (invalid schema). After the fix, all four pass. The glossary context files contain the required anchors and the tactic YAML validates against the schema.

**Expected**: Glossary and tactic files satisfy the integrity constraints enforced by the test suite.

### Scenario 5 — Charter synthesizer fix verified (#1303)

A developer runs `pytest tests/charter/synthesizer/ -q` repeatedly and observes that synthesizer manifest hashes are stable across runs and that all five cluster tests pass. Path-guard coverage is confirmed by the chokepoint test.

**Expected**: Synthesizer output is deterministic; path_guard is the sole write boundary.

### Scenario 6 — Full-suite no-regression check

After all four clusters are fixed, the maintainer runs the full test suite and confirms the net failure count is equal to or lower than the FR-001 baseline with no previously passing tests newly broken.

**Expected**: The 3.2.0 release baseline is clean for the targeted clusters; no regressions introduced.

---

## Success Criteria

| # | Criterion |
|---|-----------|
| 1 | A refreshed baseline is documented (commit SHA, pass/fail/skip counts, cluster grouping) before any fix begins. |
| 2 | Every still-reproducing P0 cluster has a targeted test run showing zero failures after its fix. |
| 3 | At least one regression test per fixed cluster is present in the repository after the mission completes. |
| 4 | The full-suite failure count after all fixes is ≤ the count recorded in the refreshed baseline. |
| 5 | No fix introduces a `mypy --strict` error or drops test coverage below 90% for new code. |

---

## Assumptions

- The four P0 clusters (#1301, #1303, #1304, #1305) may or may not still reproduce on current `main`; FR-002 requires verification before any fix begins.
- The remaining ~190 failures from the #1298 baseline that were not sub-filed as specific P0 issues are out of scope for this mission unless they directly block fixing one of the four targeted clusters.
- The `spec_kitty_events` version mismatch (C1/C2 in the #1301 triage) may have been partially addressed by intervening commits; the baseline refresh will confirm the current state.
- Fixes that require changes to `uv.lock` or `pyproject.toml` are in scope only for the events-drift cluster (#1301).

---

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| #1298 | Tracked issue | Parent baseline tracking issue; refreshed baseline supersedes the original 217-failure count |
| `spec_kitty_events` PyPI package | External | Version pinned in `uv.lock`; must match what is installed for #1301 cluster to pass |
| `spec-kitty-runtime` (retired) | External | Per shared-package-boundary cutover, the CLI does not depend on it; #1301 fix must not reintroduce this dependency |
| `docs/01KSF9HJ-triage/triage.md` | Reference | Triage document on branch `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ`; authoritative root-cause analysis for all four clusters |
