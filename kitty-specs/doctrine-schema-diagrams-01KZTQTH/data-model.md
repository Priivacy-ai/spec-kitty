# Data Model: Doctrine Schema Diagrams (Scope B)

- **PlantUML render step**: post-DocFX, both workflows, after glossary_linker; input `_site` HTML `@start*` fences → output injected SVG (+ alt); pinned jar, SANDBOX, network-isolated.
- **Doctrine artefact model** (read-only source of truth): `AgentProfileSchema` (+nested), `MissionStep`/`MissionStepContract`, `ActionIndex` (frozen dataclass), `DRGNode`/`DRGEdge`/`NodeKind`(16)/`Relation`(15), `ArtifactKind`(12), per-kind models.
- **Schema diagram**: a `@startyaml` block bound (file:class, 1:N) to its model(s); alt derived from title/caption; drift-guarded.
- **Binding table**: the enumerated diagram→model(s) registry the guard checks for completeness.
- **Module README**: pointer-only bridge from a source module to its doctrine-kinds entry, diagram, and owning domain plan.
