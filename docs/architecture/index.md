---
title: Architecture notes
description: 'Page index for docs/architecture/: living C4 model and vision, per-version (1.x/2.x/3.x) history, explanations, assessments, connector/installation notes, and reference templates.'
doc_status: active
updated: '2026-07-22'
related:
- docs/adr/3.x/adr-connector-auth-binding-separation.md
- docs/adr/3.x/adr-github-app-installation-authority.md
- docs/architecture/README.md
- docs/architecture/feature-detection.md
- docs/architecture/gap-analysis-connector-installation-model.md
- docs/index.md
---
# Architecture notes

Internal architecture and design notes for Spec Kitty subsystems. These pages capture
design rationale and gap analyses; they are working engineering material rather than
end-user documentation. This index enumerates every page in `docs/architecture/`
(the section's curated-complete index — see [`README.md`](README.md) for the
boundary rule and layout).

## Living architecture (current + forward)

- [Architecture](README.md) — the canonical corpus landing page: the `architecture/` vs `docs/` boundary rule and living-at-top / versioned-history-beneath model.
- [Architecture Vision (living)](vision/README.md) — current and future forward intent, above versioned history.
- [Architecture Diagrams (living C4)](diagrams/README.md) — the living C4 model for the current 3.x architecture.
- [Diagrams: 3.x System Context](diagrams/01_context/README.md) — living C4 level 1.
- [Diagrams: 3.x Containers](diagrams/02_containers/README.md) — living C4 level 2.
- [Diagrams: 3.x Runtime/Execution Domain](diagrams/02_containers/runtime-execution-domain.md) — living C4 level 2 container detail.
- [Diagrams: 3.x Components](diagrams/03_components/README.md) — living C4 level 3.

## Versioned history — 3.x

- [Architecture 3.x](README-3.x.md) — landing page for the 3.x track (since the 3.0.0 release).
- [3.x — vision (history slot)](vision/README-3.x.md) — the 3.x era's settled vision history.

## Versioned history — 2.x

- [Architecture 2.x](README-2.x.md) — landing page for the 2.x architecture track.
- [2.x — vision (history slot)](vision/README-2.x.md) — per-era vision record for 2.x.
- [2.x System Landscape](00_landscape/README.md) — C4 level 0 historical snapshot.
- [2.x System Context](01_context/README.md) — C4 level 1 historical record.
- [2.x Containers](02_containers/README.md) — C4 level 2 historical decomposition.
- [2.x Runtime/Execution Domain](02_containers/runtime-execution-domain.md) — C4 level 2 historical container detail.
- [2.x Components](03_components/README.md) — C4 level 3 historical breakdown.
- [2.x Implementation Mapping](04_implementation_mapping/README.md) — C4 level 4 historical link from components to code.
- [Core Code Patterns Applied in the Codebase](04_implementation_mapping/code-patterns.md) — recurring implementation idioms mapped to components (2.x-era record).

## Versioned history — 1.x

- [Architecture 1.x](README-1.x.md) — landing page for the legacy 1.x architecture record.
- [1.x — vision (history slot)](vision/README-1.x.md) — per-era vision record for 1.x.

## Explanations

- [Explanation](explanation-index.md) — the Divio "understanding-oriented" hub for this section.
- [Spec-driven development](spec-driven-development.md) — the core methodology.
- [Mission system](mission-system.md) — how missions and work packages relate.
- [Mission-type resolution](mission-type-resolution.md) — the doctrine → charter → core seam.
- [Execution lanes](execution-lanes.md) — the lane-based parallel execution model.
- [Git worktrees](git-worktrees.md) — what worktrees share and keep separate.
- [Git workflow: who does what](git-workflow.md) — infrastructure git vs content git.
- [Multi-agent orchestration](multi-agent-orchestration.md) — coordinating work across agents.
- [Kanban workflow](kanban-workflow.md) — the nine lanes and their transitions.
- [The runtime loop](runtime-loop.md) — how `spec-kitty next` inverts control.
- [AI agent architecture](ai-agent-architecture.md) — how Spec Kitty stays agent-agnostic across agents.
- [Why the Divio documentation system?](divio-documentation.md) — tutorials/how-to/reference/explanation mapping.
- [Doctrine relationships](doctrine-relationships.md) — DRG relation types as typed graph edges.
- [Understanding the org doctrine layer](org-doctrine-layer.md) — built-in/org/project doctrine resolution.
- [Understanding Charter: synthesis, DRG, and governed context](charter-synthesis-drg.md).
- [Understanding governed profile invocation](governed-profile-invocation.md) — standalone dispatch under governance.
- [Documentation Mission Guide](documentation-mission.md) — the Documentation Kitty mission.
- [Understanding the retrospective learning loop](retrospective-learning-loop.md) — the four-category model.
- [Branch-target routing](branch-target-routing.md) — which git branch receives each type of change.
- [WP runtime-state eviction](wp-runtime-state-eviction.md) — evicting runtime-mutable state into the event log.
- [Launch-readiness behavior (coming soon)](launch-readiness-future.md) — pre-launch Teamspace design intent.
- [Architecture: centralized feature detection](feature-detection.md) — how Spec Kitty detects project frameworks and capabilities.

## Connector & installation notes

- [Gap analysis: connector installation model](gap-analysis-connector-installation-model.md) — open gaps in the installation-link-mapping-override connector model.
- [Connector auth / binding separation](../adr/3.x/adr-connector-auth-binding-separation.md) — separating connector authentication from binding.
- [GitHub App installation authority](../adr/3.x/adr-github-app-installation-authority.md) — installation-authority model for the GitHub App.

## Assessments

- [Code as a Crime Scene — High-Level Overview](assessments/code-as-a-crime-scene-overview.md) — pedagogical overview of the CaaCS auditing technique (durable methodology explainer; the dated 2026-05 forensic run itself lives under [`docs/plans/engineering-notes/architecture-audits/`](../plans/engineering-notes/architecture-audits/), see FR-002 verdict below).

## Calibration reports

- [Calibration Report Template](calibration/README.md) — the §4.5.1 inequality-check template, created/updated by WP10.
- [Calibration Report: documentation](calibration/documentation.md).
- [Calibration Report: erp-custom](calibration/erp-custom.md).
- [Calibration Report: research](calibration/research.md).
- [Calibration Report: software-dev](calibration/software-dev.md).

## Ownership & charter models

- [Functional Ownership Map](05_ownership_map.md) — which code slices own which functional areas.
- [Unified Charter Bundle](06_unified_charter_bundle.md) — the single-file authoritative `charter.yaml` model.

## Templates & reference

- [ADR template](adr-template.md) — the shared ADR authoring template used by all tracks.
- [Pip vs pipx vs uv](pip-vs-pipx-vs-uv.md) — which installer to use for the Spec Kitty CLI.

## Retired / redirect guides

- [Architecture Documentation Guide](ARCHITECTURE_DOCS_GUIDE.md) — retired 2.x-era guide; redirects to the documentation home and `llms.txt`.
- [Architecture Navigation Guide](NAVIGATION_GUIDE.md) — retired 2.x-era guide; redirects to the documentation home and `llms.txt`.

## See also

- [Documentation home](../index.md)
- [Architecture Decision Records](../adr/3.x/README.md)
