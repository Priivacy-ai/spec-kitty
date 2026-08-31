---
title: Reference (contributor policy & ledgers)
description: Reference material for maintainers — friction inventories, coverage-signal reconciliation, seam ledgers, standing orders, red-main policy, and terminology exemptions.
doc_status: active
updated: '2026-08-31'
audience: docs/context/audience/internal/maintainer.md
related:
- docs/development/index.md
- docs/development/how-to/index.md
- docs/development/testing/index.md
---
# Reference (contributor policy & ledgers)

Look-up material a maintainer consults rather than reads front-to-back: standing
policy, exemptions, and the classification ledgers that pin how the codebase is
kept honest.

- [Known current friction points](known-friction-points.md) — the fast-drifting list of current repo/tooling gotchas an agent hits mid-mission.
- [Coverage signals](coverage-signals.md) — reconciling the internal diff-coverage gate with SonarCloud coverage / new_coverage.
- [`tests/sync/` process-global and thread-seam inventory (#3115)](process-global-inventory-3115.md) — a narrowed inventory of process-global mutable state and thread-spawning seams in the `tests/sync/` cone.
- [Quality & tech-debt standing orders](quality-and-tech-debt-standing-orders.md) — the eight standing practices for spec-driven missions.
- [Read-side placement-seam classification ledger](read-side-seam-classification.md) — per-site verdicts for every production call site that bypasses `PlacementSeam.read_dir(kind)`.
- [Red main and release readiness](red-main-and-release-readiness.md) — what a red `main` means and why CI status is the release authority.
- [Terminology guard exemption policy](terminology-exemptions.md) — surfaces exempted from the terminology drift guards.

## Docs site publication source

> **Temporary publication gap (3.2.6 convergence).** `docs.spec-kitty.ai` is
> deployed by `.github/workflows/docs-pages.yml` from upstream `main`, not from
> this EXPERIMENTAL fork. Between the first promotion to upstream and the
> workflow-restoration child landing, the public site can remain stale. This is
> accepted for 3.2.6; the owner announcement covers the gap, and the
> workflow-restoration child is the follow-up.

## See also

- [Development home](../index.md)
- [How-to runbooks](../how-to/index.md)
