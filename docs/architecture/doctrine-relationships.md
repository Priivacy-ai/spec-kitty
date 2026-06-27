---
title: 'Doctrine relationships: lineage, delegation, and augmentation'
description: "How Spec Kitty models doctrine lineage, delegation, and augmentation as typed DRG edges (specializes_from, delegates_to, enhances/overrides) rather than artifact fields."
doc_status: active
updated: '2026-06-03'
---
# Doctrine relationships: lineage, delegation, and augmentation

This page explains how relationships between doctrine artifacts are modelled in
Spec Kitty, and — importantly — **how to author them**. As of the org-doctrine
profile-integrity work (FR-001/FR-003/FR-004, NFR-007), every relationship is a
**typed edge in the Doctrine Reference Graph (DRG)**. Relationships are *not*
authored as fields on the artifacts themselves.

> **One authoring surface.** Author relationships as DRG **fragment edges** in
> `graph.yaml` (built-in / project tier) or `drg/fragment.yaml` (org-pack tier).
> The deprecated `enhances:` / `overrides:` / `specializes-from:` *artifact
> fields* are being retired (they become a hard error). The canonical relation
> tokens live on the `Relation` enum in
> [`src/doctrine/drg/models.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/doctrine/drg/models.py).

## The three relationship families

Lineage, delegation, and augmentation are three **distinct** concepts and must
never be conflated. The DRG keeps them as separate relation types so traversal
never accidentally crosses from one to another.

### Lineage — `specializes_from`

A *static composition* relation: one artifact (typically an agent profile)
**derives from** a parent, narrowing or extending it. Resolution walks the
lineage chain and merges inherited fields from the ancestor toward the
descendant.

- **Direction:** `child --specializes_from--> parent`.
- **Use it for:** specialist agent profiles built on a base profile (for
  example, a language-specific implementer that specialises a generic
  implementer).
- **Do not use it for:** runtime handoff. Lineage is composition at load time,
  not delegation at execution time.

```yaml
# graph.yaml (built-in tier) — lineage authored as an edge
edges:
  - source: agent_profile:python-pedro
    target: agent_profile:implementer-ivan
    relation: specializes_from
    reason: Python Pedro is a language-specialist implementer derived from Implementer Ivan
```

### Delegation — `delegates_to`

A *runtime handoff* relation: at execution time one agent hands work to another.
Delegation is **never inferred from lineage** — a child profile does not
implicitly delegate to its parent, and a parent does not implicitly delegate to
its children. If a handoff should happen, it is authored explicitly.

- **Direction:** `from --delegates_to--> to`.
- **Use it for:** an orchestrating profile that routes a sub-task to a
  specialist at runtime.

### Augmentation — `enhances`, `overrides` (and legacy `replaces`)

An *overlay* relation pair, used when a higher layer (an org pack or project
tier) adjusts a built-in artifact:

- **`enhances`** — *field-level merge*. The overlay's fields replace the
  same-named fields of the target; fields the overlay omits fall through from the
  base. For topology-bearing kinds (mission step contracts, mission types) the
  action sequence is preserved: an `enhances` overlay may reorder but must not
  silently drop a base step or strip a step's input/output contract (FR-029 —
  the merge fails closed rather than corrupting the topology).
- **`overrides`** — *full replacement*. The overlay replaces the target
  artifact in its entirety.
- **`replaces`** — retained only for backward compatibility with existing
  hand-authored fragments.

Augmentation edges may be authored against **every** augmentation-eligible kind:
directives, tactics, styleguides, toolguides, paradigms, procedures, agent
profiles, mission step contracts, and mission types.

```yaml
# drg/fragment.yaml (org-pack tier) — augmentation authored as edges
edges:
  - source: directive:org-directive
    target: directive:org-directive
    relation: enhances
    reason: Directive overlay enhances a built-in directive
  - source: mission_type:org-mission-type
    target: mission_type:org-mission-type
    relation: overrides
    reason: Mission-type overlay replaces a built-in mission type
```

## Why edges, not fields

Authoring relationships as artifact fields made the relationship invisible to
the graph until each artifact was individually parsed, and split the same
concept across several field spellings (`specializes-from`, `enhances`,
`overrides`). Modelling every relationship as a DRG edge gives a single,
queryable, layer-aware authority:

- **One source of truth.** The merged DRG is the only place relationships live;
  there is no field-vs-edge ambiguity.
- **Zero-loss migration (NFR-007).** Every previously field-authored
  relationship maps to exactly one merged edge. The migration test
  (`tests/doctrine/test_relationship_migration.py`) discovers the field-authored
  set from the built-in artifacts and proves each one has a corresponding edge —
  it never trusts a hardcoded count.
- **Fail-closed semantics (FR-003).** An edge whose `relation` token is not a
  recognised member of the `Relation` enum is rejected loudly at load time
  rather than being silently dropped.

## Canonical authoring example

Two profiles, one lineage edge:

```yaml
# graph.yaml
nodes:
  - urn: agent_profile:implementer-ivan
    kind: agent_profile
    label: Implementer Ivan
  - urn: agent_profile:python-pedro
    kind: agent_profile
    label: Python Pedro
edges:
  - source: agent_profile:python-pedro
    target: agent_profile:implementer-ivan
    relation: specializes_from
```

Org packs use the same model in `drg/fragment.yaml`, addressing nodes by their
short `id` + plural `kind`; the merge bridges those to canonical `kind:id` URNs.

## Living documentation

Per `DIRECTIVE_037` (living-documentation sync), this page is kept in step with
the `Relation` enum and the migration tests. When a relation type is added,
removed, or its semantics change, update:

1. the `Relation` enum docstring in `src/doctrine/drg/models.py`,
2. this explanation page, and
3. the relationship-migration tests and fixtures
   (`tests/doctrine/test_relationship_migration.py`,
   `tests/doctrine/fixtures/relationship_packs/`).
