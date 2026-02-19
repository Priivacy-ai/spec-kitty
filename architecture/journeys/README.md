# Spec Kitty Architecture: User Journeys

> This directory contains **user journey descriptions** that contribute to
> the evolution and refinement of the Spec Kitty system.
>
> These are architectural design artifacts — they capture how users (human
> and AI) interact with spec-kitty across phases, system boundaries, and
> coordination concerns. They inform feature design, mission templates,
> and CLI command structure.

## Purpose

User journeys in this directory serve three roles:

1. **Design input** — They describe how the system *should* work, driving
   feature specifications and implementation priorities.
2. **Alignment check** — They validate that new features serve the end-to-end
   user experience, not just isolated commands.
3. **Living documentation** — They evolve as spec-kitty evolves, capturing
   the intended workflow at each stage of the system's maturity.

## Template

Journeys follow the [User Journey Template](../../src/specify_cli/missions/design/templates/user-journey-template.md),
which captures:

- **Actors** (with type annotations and persona links)
- **Journey Map** (phase table with events)
- **Coordination Rules**
- **Responsibilities** (split by system boundary)
- **Acceptance Scenarios** (BDD format)
- **Design Decisions** (linked to ADRs)

## Status Lifecycle

| Status | Meaning |
|--------|---------|
| `DRAFT` | Proposed journey, under discussion |
| `REVIEW` | Journey reviewed against implementation feasibility |
| `ACCEPTED` | Journey approved as target design — drives feature work |
| `IMPLEMENTED` | Journey fully realized in spec-kitty commands and workflows |

## Index

| Journey | Status | Description |
|---------|--------|-------------|
| [Project Onboarding & Bootstrap](001-project-onboarding-bootstrap.md) | DRAFT | New project setup: init → bootstrap (vision + constitution) → first feature |
| [System Architecture Design](002-system-architecture-design.md) | DRAFT | Architectural structure and boundary design after bootstrap |
| [System Design & Shared Understanding](003-system-design-and-shared-understanding.md) | DRAFT | Design mission flow for glossary, journeys, and ADR alignment |
| [Curating External Practice into Governance](004-curating-external-practice-into-governance.md) | DRAFT | Pull-based adoption flow for external practices (e.g., ZOMBIES TDD) via curation + constitution activation |

## Relationship to Other Architecture Artifacts

- **ADRs** (`architecture/adrs/`) — Individual design decisions; journeys may reference multiple ADRs
- **Feature Specs** (`kitty-specs/`) — Per-feature specifications; journeys span multiple features
- **Mission Templates** (`src/specify_cli/missions/`) — Journeys inform which missions and phases are needed
