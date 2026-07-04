---
title: Guides
description: 'Durable how-to guides for Spec Kitty: testing workflows, review gates, contract pinning, cross-package local development, and maintainer runbooks.'
doc_status: active
updated: '2026-07-04'
related:
- docs/configuration/index.md
- docs/guides/contract-pinning.md
- docs/guides/local-overrides.md
- docs/guides/pr-landing.md
- docs/guides/review-gates.md
- docs/guides/testing-flakiness.md
- docs/guides/testing-parallel.md
- docs/index.md
- docs/operations/index.md
- docs/plans/index.md
---
# Guides

Durable contributor and maintainer how-tos and workflow guides — task-oriented
pages that outlive any single mission. For effort-scoped working notes
(audits, debriefs, investigations) see [`../plans/`](../plans/index.md).

## Contributor guides

- [Test-flakiness handling policy](testing-flakiness.md) — detection tiers and the never-retry-to-green rule.
- [Running the test suite in parallel](testing-parallel.md) — the parallel-run workflow and volume gates.
- [Contract pinning workflow](contract-pinning.md) — pinning observable contracts in tests.
- [Review gates](review-gates.md) — the pre-PR / pre-review checklist.
- [Local overrides for cross-package development](local-overrides.md) — dev-only editable installs that must never be committed.

## Maintainer guides

- [Landing contributor PRs](pr-landing.md) — the claim → isolate → rebase → classify → fold → squad → hand-off runbook, with field-tested gotchas.

## See also

- [Documentation home](../index.md)
- [Operations](../operations/index.md)
- [Configuration](../configuration/index.md)
