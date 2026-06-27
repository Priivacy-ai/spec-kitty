---
title: Architecture Diagrams (living C4)
description: The living C4 model for the current 3.x architecture, carried forward from the 2.x snapshot and refreshed in place against the ratified 3.x domain model.
doc_status: active
updated: '2026-06-15'
related:
- docs/architecture/README.md
- docs/architecture/diagrams/01_context/README.md
- docs/architecture/diagrams/02_containers/README.md
- docs/architecture/diagrams/03_components/README.md
---
# Architecture Diagrams (living C4)

This directory holds the **living C4 model** for the **current 3.x architecture**.
It was carried forward from the 2.x snapshot and refreshed in place against the
ratified 3.x domain model. It is part of the *living architecture at the top* of
`architecture/` (see [`../README.md`](../README.md)).

The numbered C4 levels are kept stable so navigation and tooling stay predictable:

| Level | Directory | Scope |
|---|---|---|
| C4 L1 — Context | [`01_context/`](01_context/README.md) | System boundary, actors, external interactions |
| C4 L2 — Containers | [`02_containers/`](02_containers/README.md) | The four bounded modules + the Op execution tier |
| C4 L3 — Components | [`03_components/`](03_components/README.md) | Component-level behavior sequences |

## The 3.x domain model these diagrams depict

The model is the **four bounded modules** ratified in
[`../3.x/adr/2026-06-03-1-execution-state-domain-model.md`](../../adr/3.x/2026-06-03-1-execution-state-domain-model.md):

| Module | Domain responsibility |
|---|---|
| **Governance** | Charter and Doctrine artifacts — what the project is allowed to do and how |
| **Mission Management** | Mission lifecycle, WP status/kanban, status events, planning artifacts |
| **Execution / Runtime** | Workspace resolution, branch state, mission-run lifecycle, CWD-invariant context |
| **Shared Kernel** | Value types, identifiers, and utilities shared across modules — no domain logic |

Modules communicate via **Open Host Service (OHS) facades** only; direct
cross-module imports of internal submodules are prohibited by architectural tests.
Status and kanban are owned **exclusively by Mission Management** (the `status/`
OHS facade). The canonical execution-state surface is the top-level
[`mission_runtime`](../../adr/3.x/2026-06-07-1-execution-state-canonical-surface.md)
package. The **Op execution tier** (`spec-kitty dispatch` plus
`profile-invocation complete` and the pre/post-mission lifecycle) sits across
the modules as the shared Op shape.

## Convention

- **Hand-authored Markdown + Mermaid** (renders on GitHub, no build tooling) — R-04.
- Each level uses a single canonical `README.md` entrypoint; additional detail
  pages may live beside it.
- The 2.x snapshot under `architecture/2.x/{01_context,02_containers,03_components}/`
  is frozen as history; this living copy is the one refreshed against the
  current 3.x domain model.

> Deterministic diagram **generation** (Structurizr/PlantUML) is deliberately out
> of scope here — see upstream `#1839` (deduped vs `#1812`). This living C4 stays
> hand-authored per R-04; the generated-C4 swap is cross-referenced only.
