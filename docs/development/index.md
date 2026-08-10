---
title: Development
description: The contributor/maintainer zone for Spec Kitty — subdivided into getting-started, how-to runbooks, reference policy, and testing — kept separate from end-user guides.
doc_status: active
updated: '2026-08-10'
audience: docs/context/audience/internal/maintainer.md
related:
- docs/development/getting-started/index.md
- docs/development/how-to/index.md
- docs/development/reference/index.md
- docs/development/testing/index.md
- docs/guides/index.md
---
# Development

Runbooks and policy for people **contributing to or maintaining the Spec Kitty
project itself** — as opposed to [`../guides/`](../guides/index.md), which
documents *using* Spec Kitty in your own project. This strict split is FR-003:
no contributor-only page is reachable from end-user navigation.

This zone is subdivided by concern:

- **[Getting started](getting-started/index.md)** — [onboarding a co-maintainer](getting-started/onboarding-run.md) and [isolated dev environments](getting-started/isolated-dev-environments.md).
- **[How-to](how-to/index.md)** — task runbooks: [landing PRs](how-to/pr-landing.md), [review gates](how-to/review-gates.md), [local overrides](how-to/local-overrides.md), [the issue tracker](how-to/manage-issue-tracker.md), [contract pinning](how-to/contract-pinning.md), [the cut-over guard](how-to/cutover-guard.md), and [creating a doctrine artifact](how-to/create-a-doctrine-artifact.md).
- **[Reference](reference/index.md)** — policy and ledgers: [friction points](reference/known-friction-points.md), [coverage signals](reference/coverage-signals.md), [the #3115 seam inventory](reference/process-global-inventory-3115.md), [standing orders](reference/quality-and-tech-debt-standing-orders.md), [the read-side seam ledger](reference/read-side-seam-classification.md), [red-main policy](reference/red-main-and-release-readiness.md), and [terminology exemptions](reference/terminology-exemptions.md).
- **[Testing](testing/index.md)** — [flakiness policy](testing/testing-flakiness.md), [parallel runs](testing/testing-parallel.md), [mutation tests](testing/run-mutation-tests.md), [UI e2e](testing/ui-e2e.md), and [time-dependent tests](testing/write-time-dependent-tests.md).

## Start here

- [Contributing to Spec Kitty](contributing.md) — developer setup, running tests, submitting PRs, AI-assistance disclosure, and the release process.

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
