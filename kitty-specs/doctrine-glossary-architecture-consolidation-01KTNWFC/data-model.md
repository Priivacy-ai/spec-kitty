# Data Model — Doctrine, Glossary & Architecture Consolidation

This mission's "entities" are **artefact and schema shapes**, not runtime records. Captured here for the design phase.

## Doctrine artefacts (IC-04)
- **Procedure / Tactic / Styleguide / Toolguide** — doctrine artefacts under `src/doctrine/<kind>/`, each conforming to its doctrine schema (`src/doctrine/schemas/*.schema.yaml`) and registered as DRG nodes/edges.
  - Fields (per schema): id, kind, name, description, body/sections, relationships (DRG edges: `requires`/`suggests`/`specializes_from` as applicable).
  - Invariant: every authored artefact has a DRG node + at least one edge after IC-08 re-curation.

## Architecture layout (IC-02/IC-03)
- **Living architecture** (top-level): `vision/`, `audience/`, `diagrams/` (C4 levels 01_context/02_containers/03_components, Markdown+Mermaid), `README.md` (boundary rule).
- **Versioned history**: `architecture/<version>/{adr,vision,research}` — immutable; decay target for demoted content.
- **ADR** (IC-05): file under `architecture/3.x/adr/`, conforming to `architecture/adr-template.md`.
- State transition (content lifecycle): `living (top-level) → demoted to architecture/<version>/ when no longer current/future` (never deleted).

## Glossary (IC-01/IC-06)
- **Canonical surface**: top-level `glossary/` (+ `contexts/`). Single source of truth (C-005).
- **Seed**: `terms: [{surface(lowercase), definition, confidence, status}]`; validated by `spec-kitty glossary validate`.
- **GlossaryScope**: enum (`mission_local`, `team_domain`, `audience_domain`, `spec_kitty_core`). Planning-and-tracking subset stays a non-registered reference (FR-011 defer); promotion = new enum value (out of scope this mission).

## Charter config (IC-07)
- **org-charter.yaml `extends:`** — list of base-org references; merge = **additive**, base-org precedence, cycle-detected. Resolved through `charter.activation_engine` plan/commit + cascade (no parallel resolver).
- Invariant: extend resolution is non-destructive (C-004); cycles rejected fail-closed.

## DRG (IC-08)
- **graph.yaml** — generated nodes/edges over doctrine artefacts + profiles; freshness-tested. Regeneration command produces deterministic output; profile-edge detection symmetric (A→B implies the reverse edge is checked).

## Reference-rewrite surface (IC-01/IC-02 — bulk_edit)
- Old→new path map of every glossary/architecture reference (charter authority paths, `src/glossary` loader, `.kittify/glossaries`, doctrine/doc cross-links). Enumerated in `occurrence_map.yaml`.
