---
# doc_status is deliberately `active`, NOT `durable`: this is a living navigation
# page whose catalogue grows as new domain throughlines are added. The plans it
# lists are the durable artefacts; the index itself is a mutable nav surface, so it
# must not be "fixed" to durable by a later curator.
title: 'Domain Throughlines — Catalog'
description: 'One-hop catalog of the durable, version-spanning domain throughlines under docs/plans/domains/: SaaS & hosted sync, doctrine & charter, packs extraction, and API & dashboard.'
doc_status: active
updated: '2026-08-12'
related:
- docs/plans/index.md
- docs/plans/domains/doctrine-charter-domain-plan.md
- docs/plans/domains/packs-extraction-domain-plan.md
- docs/plans/domains/api-dashboard-domain-plan.md
---
# Domain Throughlines — Catalog

**Domain throughlines** are the durable, version-spanning strategy for a domain. Each
holds the standing "why" — invariants, sub-areas, and cross-references — and points at
the release-scoped epics and roadmaps for the "what ships when" rather than duplicating
them. Unlike the distil-then-retire working notes elsewhere under
[`docs/plans/`](../index.md), a throughline does **not** retire when a milestone closes.

This page is the one-hop catalog of every throughline. Naming convention:
`<domain>-domain-plan.md`, filed here under `domains/`.

## The throughlines

- **SaaS & Hosted Sync** — domain plan retired 2026-09-06 (Convergence #3881): the local
  sync transport was removed and the hosted surface re-homed to the authoritative upstream
  repos (`spec-kitty/zeitgeist`, `spec-kitty/saas`). See the
  [convergence-retirement ADR](../../adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md).
- **[Doctrine & Charter — Domain Plan](doctrine-charter-domain-plan.md)** — the
  governance substrate: charter lifecycle & sole-door access, pack extensibility,
  activation-driven availability, `meta.json` fail-closed reads, the stable public API
  surface, and glossary-as-doctrine.
- **[Packs Extraction — Domain Plan](packs-extraction-domain-plan.md)** — physically
  extracting the doctrine layer into the standalone `spec-kitty-doctrine` module:
  boundary definition, import-cycle break, strangler cutover, and repo split.
- **[API & Dashboard — Domain Plan](api-dashboard-domain-plan.md)** — the stable
  application/mission-data API surface (#645) and the dashboard/UX consumers (#650),
  including retiring the Feature-labelled UI drift.

## See also

- [Plans landing page](../index.md) — the full plans surface (throughlines plus the
  distil-then-retire working collections).
