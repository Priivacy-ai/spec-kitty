# Data Model: docs/plans Closeout and Doctrine Schema Diagrams

This mission is docs + tooling; the "data" is documents, frontmatter, and the doctrine
code models the diagrams depict. Entities and their invariants:

## DocStatus (enum)

- **Represents**: the lifecycle state of a docs page (`scripts/docs/frontmatter_backfill.py:DocStatus`).
- **Fields/values**: existing (`active`, `draft`, `deprecated`, `superseded`/`closeout` per corpus usage) + **new** `durable`.
- **Invariant**: every validation site (styleguide contract, structural lint, freshness/tests) accepts the full set; `durable` is exempt from the retire sweep.

## Domain plan (throughline)

- **Represents**: a durable, version-spanning plan for one domain.
- **Fields**: frontmatter (`title`, `description` ≤180 chars, `doc_status: durable`, `updated`, `related:`); body in the canonical section shape (§1 purpose/scope → §6 cross-refs).
- **Location invariant**: lives under `docs/plans/domains/`; reachable in one hop from `docs/plans/index.md`.
- **Instances**: `saas-hosted-sync`, `doctrine-charter` (migrated), `packs-extraction`, `api-dashboard` (new).
- **Boundary invariant**: packs-extraction non-goals doctrine-charter §3.2; api-dashboard non-goals doctrine-charter §3.6.

## Retire candidate

- **Represents**: a `docs/plans` document/cluster proposed for retirement.
- **Fields**: path, backing-evidence citation (shipped/distilled/superseded), retire mechanism (`marker-in-place` | `move-to-archive`), status (`retired` | `deferred` | `not-retireable`).
- **Invariant (NFR-005)**: content is never deleted; retirement preserves it and carries evidence. The roadmap is `deferred` (C-001).

## Doctrine artefact model (source of truth)

- **Represents**: the frozen code model for an artefact kind.
- **Key attributes**: `frozen=True, extra="forbid"` (closed field set); field names, types, required/optional, enum values, nesting.
- **Instances**: `AgentProfileSchema`, `MissionType`/`MissionStep`/`MissionStepContract`, `ActionIndex`, `DRGNode`/`DRGEdge`/`NodeKind`/`Relation`, `ArtifactKind`, per-kind models.
- **Invariant**: read-only in this mission — the diagrams follow the model, never the reverse.

## Schema diagram

- **Represents**: a `@startyaml` typed-placeholder rendering of an artefact model, embedded in a doctrine doc page.
- **Fields**: the `@startyaml` source block; the model it binds to (for the drift guard); the host page + section.
- **Invariant (NFR-001)**: the diagram's field set equals the bound model's field set (drift guard fails otherwise).

## PlantUML render step

- **Represents**: the build-time post-DocFX HTML post-processor (`scripts/docs/plantuml_render.py`).
- **Behaviour**: input = `docs/_site` HTML with `@start*` fenced blocks; output = the same HTML with each block replaced by a rendered `<svg>`/`<img>`; uses a pinned local `plantuml.jar` (`SANDBOX`).
- **Invariants**: zero network egress (NFR-002); ≤60s added build time (NFR-003); Mermaid blocks untouched (NFR-004); SVGs generated, not committed.
