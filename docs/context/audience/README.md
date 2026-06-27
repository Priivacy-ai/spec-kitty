# Architecture Audience

This directory captures architecture-level personas for Spec Kitty.
Personas are split into two groups:

- `internal/` for contributors and system actors inside the Spec Kitty delivery boundary.
- `external/` for stakeholders outside that boundary.

Use these persona documents as the canonical audience reference for:

- actor mapping in `architecture/2.x/user_journey/*.md`
- trade-off validation in architecture decisions
- communication and adoption planning for architecture changes

## Audience Groups

| Group | Scope | Index |
|---|---|---|
| Internal Audience | Contributors and runtime/system actors | [internal/README.md](internal/README.md) |
| External Audience | Stakeholders outside runtime boundary, including evaluators for adoption decisions | [external/README.md](external/README.md) |

## Conventions

1. Persona links used in actor tables must point to files under `architecture/audience/internal/` or `architecture/audience/external/`.
2. Personas are architecture artifacts, not user-marketing profiles.
3. Keep persona behavior aligned with active ADRs and user journeys.
