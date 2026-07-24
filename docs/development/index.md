---
title: Development
description: The contributor/maintainer zone for Spec Kitty — landing PRs, the test suite, release process, and CI/operator internals — kept separate from end-user guides.
doc_status: active
updated: '2026-07-22'
related:
- docs/configuration/index.md
- docs/guides/index.md
- docs/index.md
- docs/operations/index.md
- docs/plans/index.md
---
# Development

Runbooks and policy for people **contributing to or maintaining the Spec Kitty
project itself** — as opposed to [`../guides/`](../guides/index.md), which
documents *using* Spec Kitty in your own project. This strict split is FR-003:
no contributor-only page is reachable from end-user navigation.

## Contributing

- [Contributing to Spec Kitty](contributing.md) — developer setup, running tests, submitting PRs, AI-assistance disclosure, and the release process.
- [Review gates: pre-PR / pre-review checklist](review-gates.md) — the hygiene steps to run locally before requesting review.
- [Local overrides for cross-package development](local-overrides.md) — dev-only editable installs across `spec-kitty-cli`/`-events`/`-tracker` that must never be committed.

## Maintainer guides

Runbooks scoped to maintainers (and agents acting in a maintainer capacity), not general contributors.

- [Landing contributor PRs](pr-landing.md) — the claim → isolate → rebase → classify → fold → squad → hand-off maintainer runbook.
- [Onboarding run](onboarding-run.md) — a reusable priming prompt and 12-step SDD cadence for onboarding a prospective co-maintainer.
- [Known current friction points](known-friction-points.md) — the fast-drifting list of current repo/tooling gotchas an agent hits mid-mission.
- [Managing the issue tracker](manage-issue-tracker.md) — epics vs. meta-trackers, native sub-issue parenting, and triage conventions.

## Testing the Spec Kitty codebase

- [Test-flakiness handling policy](testing-flakiness.md) — detection tiers and the never-retry-to-green rule.
- [Running the test suite in parallel](testing-parallel.md) — the parallel-run workflow and volume gates.
- [Run mutation tests locally](run-mutation-tests.md) — `mutmut`-based assertion-quality checks.
- [Write time-dependent tests](write-time-dependent-tests.md) — inject stable clocks; avoid wall-clock reads in assertions.
- [Contract pinning workflow](contract-pinning.md) — pinning the `spec-kitty-events` envelope contract in tests.
- [Coverage signals](coverage-signals.md) — reconciling the internal diff-coverage gate with SonarCloud coverage / new_coverage.

## Release and CI policy

- [Red main and release readiness](red-main-and-release-readiness.md) — what a red `main` means and why CI status is the release authority.
- [UI end-to-end tests (Playwright)](ui-e2e.md) — the dashboard browser-regression suite.
- [Quality & tech-debt standing orders](quality-and-tech-debt-standing-orders.md) — the eight standing practices for spec-driven missions.
- [Terminology guard exemption policy](terminology-exemptions.md) — surfaces exempted from the terminology drift guards.

## Non-page artifacts

- **`3-2-page-inventory.yaml`** — the page-inventory tooling artifact. It STAYS
  PUT by operator directive; the freshness/lockfile tooling
  (`scripts/docs/inventory_lockfile.py`, `check_docs_freshness.py`,
  `version_leakage_check.py`, `_inventory.py`) reads it at this stable path.
  A regression guard (`tests/docs/test_inventory_path_stable.py`) asserts the
  path cannot silently move.

## See also

- [Documentation home](../index.md)
- [Guides (end-user zone)](../guides/index.md)
