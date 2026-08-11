---
title: Plans
description: 'Plans landing page: durable domain throughlines plus the distil-then-retire working surface of investigations, research, initiatives, and release-scoped plans.'
doc_status: active
updated: '2026-08-11'
related:
- docs/plans/saas-hosted-sync-domain-plan.md
- docs/plans/doctrine-charter-domain-plan.md
- docs/plans/3-2-x-milestone-roadmap.md
- docs/changelog/release-goals.md
---
# Plans

Two kinds of document live here. **Domain throughlines** are durable and persist
across releases. Everything else is the **distil-then-retire** working surface —
investigations, research, initiatives, user journeys, and release-scoped plans that
retire once distilled into durable architecture/reference docs (Mission B, FR-009).

## Domain throughlines (version-spanning)

Domain throughlines are the standing strategy for a domain. They hold the durable
"why" — invariants, sub-areas, cross-references — and point at the release-scoped
epics and roadmaps for the "what ships when" rather than duplicating them. Epics are
release/milestone-scoped tracking, not the throughline. Unlike the working notes
below, a throughline does not retire when a milestone closes.

- **SaaS & hosted sync** — [SaaS & Hosted Sync — Domain Plan](saas-hosted-sync-domain-plan.md):
  sync & event-envelope integrity, consent & identity boundary, auth & token
  lifecycle, and hosted rollout readiness.
- **Doctrine & charter** — [Doctrine & Charter — Domain Plan](doctrine-charter-domain-plan.md):
  charter lifecycle & sole-door access, pack extensibility, activation-driven
  availability, meta.json fail-closed reads, the public API surface, and
  glossary-as-doctrine. Its release- and program-scoped companions are the
  [3.2.x Open-Core Delivery Plan](3-2-x-open-core-delivery-plan.md) and the
  [Glossary Doctrine Overhaul — Program Plan](glossary-doctrine-overhaul-program.md).
- **Packs extraction** — *(planned domain plan)*.
- **API & dashboard** — *(planned domain plan)*.

Naming convention for throughlines: `<domain>-domain-plan.md`.

## Portfolio & milestone planning

Release-scoped strategy for the current cycle. These follow the distil-then-retire
lifecycle and each links up to the domain throughline it serves.

- [3.2.x Executive Overview](3-2-x-executive-overview.md) — PO / C-suite synthesis:
  goals and progress since 3.2.4, framed as business outcomes; the top-level
  stakeholder entry point.
- [3.2.x Open-Core Delivery Plan](3-2-x-open-core-delivery-plan.md) — PO-facing status
  re-read and the open-core breaking-change delivery strategy (charter-as-sole-door,
  built-in→module extraction). Supersedes the roadmap's "G2-is-the-blocking-spine"
  framing where they disagree.
- [3.2.x Delivery Approach](3-2-x-approach.md) — cross-mission sequencing intent,
  stress-tested by a two-round dialectic squad. Doctrine-first confirmed.
- [3.2.x Milestone Roadmap](3-2-x-milestone-roadmap.md) — the operator-facing execution
  roadmap for the current milestone; the durable declarations of intent it executes
  live in [release goals](../changelog/release-goals.md).

## Working collections (by area)

Subdirectories of the distil-then-retire surface, each with its own `index.md`
cataloguing its contents. Roughly ordered by current activity:

- **[Doctrine](doctrine/index.md)** — doctrine layering, charter boundary, and
  artifact-selection planning.
- **[Refactor](refactor/index.md)** — degod/unshim program and slice-landing planning.
- **[Testing](testing/index.md)** — mutation testing, acceleration, friction audit,
  and CI gate tuning.
- **[Investigations](investigations/index.md)** — scope assessments, compatibility
  matrices, and RFC/endpoint research.
- **[Engineering notes](engineering-notes/index.md)** — runtime/state overhaul,
  surface-resolution clusters, triage logs, architectural reviews.
- **[Reviews](reviews/index.md)** — PR review resolution plans, test plans, and
  execution reports.
- **[Initiatives](initiatives/index.md)** — active architecture initiatives.
- **[User journeys](user_journey/index.md)** — end-to-end user-journey docs.
- **[Research](research/index.md)** — research deliverables (era spikes/explorations).
- **[Next-mission mappings](next-mission-mappings/index.md)** — mapping notes for the
  mission-next compatibility surface.
- **[3.2 doc publication](3-2-doc-publication/index.md)** — IA, navigation, and the
  publication checklist for the 3.2 docs cut.
