# Architectural Design: Glossary as First-Order Doctrine Artifact

**Author**: Architect Alphonso  
**Date**: 2026-05-31  
**Governing Profile**: architect-alphonso  
**Governing Directives**: DIR-001 (Architectural Integrity), DIR-031 (Context-Aware Design), DIR-032 (Conceptual Alignment)  
**Governing Paradigm**: Domain-Driven Design (domain-driven-design)  
**Design Mode**: Greenfield extension of existing doctrine architecture  
**Status**: Draft — for review before planning

---

## Initialization

*I am Architect Alphonso. I design scalable, maintainable system architectures using established design patterns and principles. I translate requirements into clear technical blueprints and architectural decision records.*

Before proceeding: per DIR-032, I am confirming the interpretation of key terms in this design request.

### Term Interpretations (DIR-032)

| Term | Interpretation Used |
|------|---------------------|
| **First-order doctrine artifact** | A glossary pack file resides in `src/doctrine/glossaries/`, participates in `ArtifactKind`, is discovered by `DoctrineService`, is addressable in the DRG, and follows the same layering (built-in → org → project) as directives, tactics, etc. |
| **Glossary pack** | A distributable YAML artifact containing curated term definitions for a domain/context boundary. Analogous to a tactic or directive file, but specialised for vocabulary. |
| **Glossary slice** | A charter activation unit: a subset of glossary packs selected for a project. "Activating a glossary slice" = activating specific glossary pack IDs via the charter system. |
| **Built-in glossary pack** | `src/doctrine/glossaries/built-in/spec-kitty-core.glossary.yaml` — ships with spec-kitty, contains the spec-kitty Ubiquitous Language. |
| **Org / project glossary** | Org and project layers of the doctrine directory: `.org/<org-name>/glossaries/*.glossary.yaml` and `.kittify/glossaries-doctrine/*.glossary.yaml`. Distinct from the existing runtime seed files at `.kittify/glossaries/<scope>.yaml`. |
| **Runtime glossary** | The existing `specify_cli/glossary/` system — dynamic, per-session semantic integrity pipeline (GlossaryStore, seeds, events). This is NOT what we are designing. |

These two concerns — **doctrine glossary artifacts** (static, distributable) and **runtime glossary state** (dynamic, per-session) — are the two bounded contexts that this design must keep separate.

---

## Problem Statement

The current glossary system exists entirely in `specify_cli/glossary/` as a runtime semantic integrity pipeline. Its terms are stored as project-local state in `.kittify/glossaries/<scope>.yaml`. There is no way to:

1. Ship a curated domain vocabulary alongside spec-kitty (the Ubiquitous Language of spec-kitty itself)
2. Distribute a "DDD vocabulary" or "team X vocabulary" as a reusable artifact
3. Activate a vocabulary slice via the charter system (same activation model as directives/tactics)
4. Allow org/project layers to extend or override the vocabulary catalog
5. Reference glossary packs from DRG edges (the `NodeKind.GLOSSARY` node kind already exists but has no artifact backing it)

The `NodeKind.GLOSSARY` kind in `src/doctrine/drg/models.py` (line 38) acknowledges that glossary entries should be DRG nodes, and `ArtifactKind` (in `artifact_kinds.py`) already has a clear extension point. The glossary DRG builder in `specify_cli/glossary/drg_builder.py` builds `glossary:*` URNs from runtime state. The missing piece is: *glossary terms as doctrine artifacts that feed into that DRG layer from a static, distributable source*.

---

## Bounded Context Map (DDD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  doctrine.*   (Catalog BC)                                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  NEW: doctrine/glossaries/                                                   │
│    built-in/spec-kitty-core.glossary.yaml  ← ships with spec-kitty          │
│    built-in/ddd-ubiquitous-language.glossary.yaml  ← optional built-in      │
│  DoctrineService.glossaries → GlossaryPackRepository                         │
│  ArtifactKind.GLOSSARY_PACK  (new enum member)                               │
│  DRG: glossary-pack:<id> nodes, VOCABULARY edges to action/tactic nodes      │
└───────────────────────┬─────────────────────────────────────────────────────┘
                        │  selection / activation
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  charter.*   (Selection BC)                                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  PackContext.activated_glossary_packs: frozenset[str] | None                 │
│  CharterPackManager.activate("glossary-pack", id, cascade)                  │
│  charter pack consistency-check: validates glossary pack IDs                 │
│  src/charter/packs/default.yaml: includes all built-in glossary packs        │
└───────────────────────┬─────────────────────────────────────────────────────┘
                        │  seeds / bootstraps
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  specify_cli/glossary.*   (Runtime Semantic Integrity BC)                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  GlossaryStore (existing — unchanged)                                        │
│  Runtime seed files: .kittify/glossaries/<scope>.yaml  (existing)            │
│  NEW: upgrade migration populates .kittify/glossaries/ from activated packs  │
│  NEW: GlossaryPackSeedLoader — loads terms from activated doctrine packs      │
│       into the runtime GlossaryStore at session start                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Boundary rule (DIR-001, DIR-031)**: `doctrine.*` never imports from `charter.*` or `specify_cli.*`. The runtime glossary (`specify_cli/glossary/`) reads doctrine glossary artifacts through the charter selection layer, not by importing from `doctrine.*` directly. The same `PackContext` threading that this mission (charter-pack-activation-layer) establishes is the mechanism.

---

## New Artifact Kind: `GLOSSARY_PACK`

### Why Not Reuse `NodeKind.GLOSSARY`?

`NodeKind.GLOSSARY` (in `doctrine/drg/models.py`) represents *individual glossary terms* as DRG nodes (URN: `glossary:<hash>`). These are runtime-derived from `specify_cli/glossary/drg_builder.py`.

`ArtifactKind.GLOSSARY_PACK` represents *a curated artifact file* — a pack of terms for a domain boundary. The distinction follows the Aggregate Design Rules styleguide: a glossary pack is an Aggregate root; individual terms are its entities.

| Concept | DRG Kind | ArtifactKind | Storage |
|---------|----------|-------------|---------|
| Individual term (runtime) | `NodeKind.GLOSSARY` | — | `GlossaryStore` (dynamic) |
| Glossary pack (static artifact) | `NodeKind.GLOSSARY_PACK` (new) | `ArtifactKind.GLOSSARY_PACK` (new) | `doctrine/glossaries/*.glossary-pack.yaml` |

### File Convention

```
src/doctrine/glossaries/
  built-in/
    spec-kitty-core.glossary-pack.yaml
    ddd-ubiquitous-language.glossary-pack.yaml  ← optional, ships empty or minimal
  <project>/                   ← project layer (local to a repo)
    team-vocabulary.glossary-pack.yaml
```

Extension: `*.glossary-pack.yaml` (distinguishes from runtime seed files `*.yaml` under `.kittify/glossaries/`).

### Artifact Schema (YAML)

```yaml
schema_version: "1.0"
id: spec-kitty-core
name: Spec Kitty Core Vocabulary
description: >
  The Ubiquitous Language of spec-kitty — terms that carry precise meaning
  within the spec-kitty bounded context.
scope: spec_kitty_core          # maps to GlossaryScope.SPEC_KITTY_CORE for runtime seeding
contexts:
  - id: mission-management
    description: Terms related to mission lifecycle and status
    terms:
      - surface: work package
        definition: >
          A discrete implementation unit within a mission, independently
          assignable to an agent. Identified by WPNN (e.g., WP01).
        synonyms_to_avoid: [task, story, ticket]
        status: active
      - surface: lane
        definition: >
          A named execution channel computed from a WP dependency graph.
          WPs in the same lane share a single git worktree.
        status: active
  - id: charter-doctrine
    description: Terms related to the charter and doctrine system
    terms:
      - surface: activation
        definition: >
          The act of marking a doctrine artifact as available for a project
          via the charter system. Activating sets the project's filtered view.
        status: active
```

---

## ArtifactKind Extension

```python
# doctrine/artifact_kinds.py — additions

_PLURALS["glossary_pack"] = "glossaries"
_PATTERNS["glossary_pack"] = "*.glossary-pack.yaml"

class ArtifactKind(StrEnum):
    # ... existing members ...
    GLOSSARY_PACK = "glossary_pack"
```

The plural `"glossaries"` maps to the directory name `doctrine/glossaries/`.

---

## DoctrineService Extension

New lazy property on `DoctrineService`:

```python
@property
def glossaries(self) -> GlossaryPackRepository:
    if "glossaries" not in self._cache:
        self._cache["glossaries"] = GlossaryPackRepository(
            built_in_dir=self._built_in_dir("glossaries"),
            org_dirs=self._org_dirs("glossaries"),
            project_dir=self._project_dir("glossaries"),
        )
    return cast(GlossaryPackRepository, self._cache["glossaries"])
```

`GlossaryPackRepository` follows the same pattern as `DirectiveRepository`, `TacticRepository`, etc. — built-in → org layers (override order) → project layer.

---

## Charter Integration (PackContext)

New field on `PackContext`:

```python
activated_glossary_packs: frozenset[str] | None = None
# None = all built-in glossary packs available (backward-compat fallback)
# non-None = only listed pack IDs available
```

`charter activate glossary-pack <id>` and `charter deactivate glossary-pack <id>` follow the same model as all other kinds.

`src/charter/packs/default.yaml` gains:

```yaml
activated_glossary_packs:
  - spec-kitty-core
  # ddd-ubiquitous-language  ← opt-in, not in default activation
```

### Cascade Semantics for Glossary Packs

- **Activation cascade to glossary-packs**: When activating a directive or tactic that has a `vocabulary:` edge to a glossary pack, `--cascade glossary-packs` also activates those packs.
- **Deactivation cascade**: Deactivating a glossary pack with `--cascade glossary-packs` only removes packs exclusively referenced by the deactivated artifact (shared-artifact protection applies as for all other kinds).

---

## DRG Integration

### New NodeKind: `GLOSSARY_PACK`

Add to `doctrine/drg/models.py`:

```python
class NodeKind(StrEnum):
    # ... existing ...
    GLOSSARY_PACK = "glossary_pack"   # NEW — URN prefix: "glossary-pack:<id>"
```

### DRG Nodes and Edges

Each `*.glossary-pack.yaml` contributes:
- One `DRGNode(urn="glossary-pack:<id>", kind=NodeKind.GLOSSARY_PACK)`
- `VOCABULARY` edges FROM tactics, directives, procedures that reference this pack

Example: `language-driven-design.tactic.yaml` currently references a `glossary-curation-interview` tactic; it should also declare a `vocabulary:` edge to `spec-kitty-core` glossary pack, because the Language-Driven Design tactic presupposes the spec-kitty vocabulary.

### `filter_graph_by_activation` Extension

`filter_graph_by_activation` (currently filters 9 kinds) gains:

```python
elif node.kind == NodeKind.GLOSSARY_PACK:
    pack_ids = pack_context.activated_glossary_packs
    if pack_ids is None:
        return True  # no restriction — all packs available
    artifact_id = node.urn.split(":", 1)[1]
    return artifact_id in pack_ids
```

---

## Runtime Seeding (Anti-Corruption Layer)

The existing `specify_cli/glossary/` runtime system is unchanged. The connection between doctrine glossary packs and the runtime `GlossaryStore` is a new loader:

```
src/specify_cli/glossary/pack_seed_loader.py

class GlossaryPackSeedLoader:
    """Loads terms from activated doctrine glossary packs into GlossaryStore."""

    def load_from_pack(
        self,
        pack: GlossaryPack,        # doctrine artifact
        store: GlossaryStore,       # runtime store
        pack_context: PackContext,  # which packs are activated
    ) -> int:                       # returns count of terms loaded
        ...
```

**Invocation point**: At session start in the glossary pipeline bootstrap (wherever `GlossaryStore` is initialized, currently in `specify_cli/glossary/pipeline.py`). The ACL translates the static pack's `TermEntry` objects into runtime `TermSense` objects with `provenance.source = "doctrine_pack"` and `confidence = 1.0`.

**Scope mapping**: Each glossary pack declares a `scope:` field that maps to `GlossaryScope`. Terms from the spec-kitty-core pack load into `GlossaryScope.SPEC_KITTY_CORE`. Org packs load into `GlossaryScope.TEAM_DOMAIN`. Project packs load into `GlossaryScope.AUDIENCE_DOMAIN` or `GlossaryScope.TEAM_DOMAIN` based on configuration.

---

## Invariants and Integrity Rules (DIR-001)

1. **Doctrine boundary**: `doctrine/glossaries/` is read-only at runtime. The runtime glossary store may derive initial state from it but must never write back.
2. **No circular import**: `specify_cli/glossary/` accesses doctrine glossary artifacts only via `DoctrineService.glossaries`, which it receives from the charter layer (PackContext-filtered). It does not import `doctrine.*` directly.
3. **Activation is authoritative**: If `activated_glossary_packs` is a non-None frozenset, `GlossaryPackSeedLoader` only loads from those packs. Runtime sessions must not load terms from deactivated packs.
4. **Runtime terms are additive**: Terms loaded from doctrine packs into `GlossaryStore` are seeds. User clarifications and session-extracted terms overlay them (scope precedence: MISSION_LOCAL > TEAM_DOMAIN > AUDIENCE_DOMAIN > SPEC_KITTY_CORE). Doctrine pack terms never override user-curated terms.
5. **Pack schema is versioned**: `schema_version: "1.0"` in every `*.glossary-pack.yaml`. Loader rejects packs with incompatible schema versions with a clear error.
6. **ID stability**: Glossary pack IDs are stable identifiers. A pack file's `id:` field must never change once published (same rule as directive IDs). Term `surface:` values within a pack must be unique.

---

## Bounded Context Vocabulary Map (DIR-031 / DIR-032)

| Term | Canonical Context | Meaning |
|------|------------------|---------|
| `glossary pack` | doctrine.* | A distributable YAML file containing curated term definitions for a domain; identified by a stable ID |
| `glossary slice` | charter.* | The activated subset of glossary packs selected for a project |
| `glossary scope` | specify_cli/glossary/* | Runtime GlossaryScope enum level (MISSION_LOCAL, TEAM_DOMAIN, etc.) — unchanged existing concept |
| `term` / `TermSense` | specify_cli/glossary/* | Runtime representation of a single term meaning in a scope |
| `term entry` | doctrine.* | Static YAML representation of a term within a glossary pack artifact |
| `built-in glossary` | doctrine.* | Glossary packs in `src/doctrine/glossaries/built-in/` |
| `pack seed loader` | specify_cli/glossary/* | The ACL component that translates static pack terms into runtime TermSense objects |

---

## Migration and Upgrade Path

1. **New migration** `m_3_2_9_default_glossary_pack`: After `m_3_2_8` (charter pack), this migration writes `activated_glossary_packs: [spec-kitty-core]` to `config.yaml` for projects that have a `.kittify/` directory.
2. **Backward compatibility**: Projects without `activated_glossary_packs` in config.yaml get `None` → all built-in glossary packs available (consistent with other kinds' fallback).
3. **Seed file compatibility**: Existing `.kittify/glossaries/<scope>.yaml` seed files are untouched. The new pack seeding is additive to them — it seeds additional terms from the doctrine layer BEFORE the project-local seed files are loaded (lower precedence).

---

## Work Package Sketch (for planning phase)

| WP | Scope | Key deliverables |
|----|-------|-----------------|
| WP-A | Doctrine layer | `ArtifactKind.GLOSSARY_PACK`, `GlossaryPackRepository`, `*.glossary-pack.yaml` schema, `spec-kitty-core.glossary-pack.yaml` built-in |
| WP-B | DRG integration | `NodeKind.GLOSSARY_PACK`, DRG loader for glossary packs, `filter_graph_by_activation` extension, VOCABULARY edges from existing tactics |
| WP-C | Charter integration | `PackContext.activated_glossary_packs`, `charter activate/deactivate glossary-pack`, default pack inclusion |
| WP-D | Runtime ACL | `GlossaryPackSeedLoader`, integration with `specify_cli/glossary/pipeline.py`, scope mapping |
| WP-E | Upgrade | `m_3_2_9_default_glossary_pack` migration, backward compatibility test |

**Dependency order**: WP-A → WP-B → WP-C → WP-D → WP-E. WP-B can parallelize with WP-C once WP-A's schema is stable.

---

## Open Questions for Next Spec Phase

1. **How many built-in glossary packs to ship?** Minimum: `spec-kitty-core`. Candidates: `ddd-ubiquitous-language`, `bdd-vocabulary`. Recommend: ship `spec-kitty-core` only; let org layers contribute domain packs. The DDD vocabulary already exists as the `domain-driven-design` paradigm — a separate glossary pack would redundantly encode it. Recommended answer: 1 built-in pack for v1.

2. **Term authority conflict**: If a runtime user-curated term (status: active, scope: TEAM_DOMAIN) conflicts with a doctrine pack term (scope: SPEC_KITTY_CORE), the runtime term wins (scope precedence: TEAM_DOMAIN > SPEC_KITTY_CORE). Is this the correct resolution? Recommend: yes, matches the "additive overlay" principle.

3. **Glossary pack cross-references**: Should a glossary pack reference other packs (e.g., a DDD pack referencing spec-kitty-core terms)? This creates a mini-DRG within the glossary layer. For v1: no cross-pack references. Packs are self-contained. Defer to v2.

4. **Context grouping in packs**: The schema shows `contexts:` (a named cluster of terms within a pack). Is this necessary for v1, or can we go flat? Recommend: include in schema but optional for v1. The built-in pack should demonstrate context grouping; downstream packs can use a flat list.

5. **`charter list` and `charter list --show-available` for glossary packs**: These commands should include glossary packs in their output. The `charter list` contract needs updating once the glossary pack kind is confirmed.

---

## ADR Reference

This design constitutes a new architectural decision. A formal ADR should be created at `architecture/adrs/2026-05-31-1-glossary-as-first-order-doctrine-artifact.md` covering:
- Context: existing glossary as runtime state, not distributable artifact
- Decision: add `ArtifactKind.GLOSSARY_PACK` and doctrine layer for static packs
- Consequences: new migration, new repository, pack-seed ACL in specify_cli
- Alternatives rejected: (a) no static layer, keep glossary purely runtime; (b) merge glossary into paradigm artifacts

---

*— Architect Alphonso*  
*Design handoff to: planner → /spec-kitty.specify for mission creation*
