# Doctrine Reference Graph (DRG)

The **DRG** models relationships between doctrine artifacts as typed graph edges
(`DRGEdge`) over addressable nodes (`DRGNode`), across the `NodeKind` and
`Relation` vocabularies. Relationships are edges, never fields on the artifacts.

This README is a **pointer** to the canonical docs — it deliberately does not
restate the schema (see the code models in this package + the drift-guarded
diagram, which are the single source of truth).

## Canonical documentation

- **Schema diagram + relation families** — [Doctrine relationships](../../../../docs/architecture/doctrine-relationships.md)
  (the `@startyaml` `DRGNode`/`DRGEdge`/`NodeKind`/`Relation` diagram is generated from these models and drift-guarded).
- **Artifact-kind / node-kind vocabulary** — [Doctrine artifact kinds](../../../../docs/architecture/doctrine-kinds.md).
- **Owning domain plan** — the doctrine-charter domain (merged on `main`).
