# Data Model: Doctrine Reference Graph (DRG)

**Mission**: DRG Phase Zero (`01KP2YCESBSG61KQH5PQZ9662H`)
**Date**: 2026-04-13

## Overview

The DRG is a directed graph where nodes are doctrine artifacts and edges are typed relationships between them. The graph is stored as a single YAML document (`graph.yaml`) and validated by Pydantic models at load time.

## Node

A node represents a single addressable doctrine artifact.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `urn` | `str` | Yes | Unique identifier in `{kind}:{id}` format |
| `kind` | `NodeKind` enum | Yes | Artifact type (derived from URN) |
| `label` | `str` | No | Human-readable display name |

### URN Format

```
{kind}:{id}
```

**Examples**:
- `directive:DIRECTIVE_001`
- `tactic:tdd-red-green-refactor`
- `paradigm:domain-driven-design`
- `styleguide:kitty-glossary-writing`
- `toolguide:efficient-local-tooling`
- `procedure:some-procedure`
- `agent_profile:implementer`
- `action:software-dev/specify`
- `action:software-dev/implement`
- `glossary_scope:project`

### NodeKind Enum

```
directive | tactic | paradigm | styleguide | toolguide | procedure |
agent_profile | action | glossary_scope
```

Alignment with `src/doctrine/artifact_kinds.py::ArtifactKind`: the DRG `NodeKind` is a superset. It includes all `ArtifactKind` values plus `action` and `glossary_scope` which are not standalone artifact types but are addressable nodes in the graph.

## Edge

An edge represents a typed, directed relationship between two nodes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | `str` | Yes | Source node URN |
| `target` | `str` | Yes | Target node URN |
| `relation` | `Relation` enum | Yes | Edge type |
| `when` | `str` | No | Applicability context (from tactic `references[].when`) |
| `reason` | `str` | No | Justification (from paradigm `opposed_by[].reason`) |

### Relation Enum (v1)

| Relation | Semantics | Traversal behavior |
|----------|-----------|-------------------|
| `requires` | Source requires target to function correctly | Transitive closure (walk until exhausted) |
| `suggests` | Source benefits from target but does not require it | Depth-limited walk (user-configurable) |
| `applies` | Source artifact applies to target action or scope | **Not populated in Phase 0.** Reserved for Phase 2+ when artifacts self-declare applicability. Direction is artifact -> action (inverse of `scope`). |
| `scope` | Action node scopes in a specific artifact | Depth 1 (defines action surface) |
| `vocabulary` | Source references glossary scope | Depth 1 (glossary injection) |
| `instantiates` | Source is a concrete instance of target pattern | Informational (not traversed by default) |
| `replaces` | Source opposes or supersedes target | Informational (conflict metadata) |
| `delegates_to` | Source delegates responsibility to target | Reserved for Phase 4 profile routing |

### Edge Extraction Mapping

How inline reference fields map to DRG edges:

| Source YAML | Field | DRG edge |
|-------------|-------|----------|
| `*.directive.yaml` | `tactic_refs: [id]` | `directive:X --requires--> tactic:id` |
| `*.directive.yaml` | `references: [{type: directive, id}]` | `directive:X --requires--> directive:id` |
| `*.directive.yaml` | `references: [{type: tactic, id}]` | `directive:X --suggests--> tactic:id` |
| `*.directive.yaml` | `references: [{type: styleguide, id}]` | `directive:X --suggests--> styleguide:id` |
| `*.tactic.yaml` | `references: [{type: tactic, id, when}]` | `tactic:X --suggests--> tactic:id` (with `when` metadata) |
| `*.tactic.yaml` | `references: [{type: styleguide, id}]` | `tactic:X --suggests--> styleguide:id` |
| `*.paradigm.yaml` | `tactic_refs: [id]` | `paradigm:X --requires--> tactic:id` |
| `*.paradigm.yaml` | `directive_refs: [id]` | `paradigm:X --requires--> directive:id` |
| `*.paradigm.yaml` | `opposed_by: [{type, id, reason}]` | `paradigm:X --replaces--> {type}:id` (with `reason` metadata) |
| `actions/*/index.yaml` | `directives: [slug]` | `action:mission/act --scope--> directive:DIRECTIVE_NNN` |
| `actions/*/index.yaml` | `tactics: [id]` | `action:mission/act --scope--> tactic:id` |
| `actions/*/index.yaml` | `styleguides: [id]` | `action:mission/act --scope--> styleguide:id` |
| `actions/*/index.yaml` | `toolguides: [id]` | `action:mission/act --scope--> toolguide:id` |
| `actions/*/index.yaml` | `procedures: [id]` | `action:mission/act --scope--> procedure:id` |

## Graph Document (graph.yaml)

Top-level YAML document structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `str` | Yes | Must be `"1.0"` |
| `generated_at` | `str` (ISO 8601) | Yes | Timestamp of last generation |
| `generated_by` | `str` | Yes | Tool that generated the graph (e.g., `"drg-migration-v1"`) |
| `nodes` | `list[Node]` | Yes | All nodes in the graph |
| `edges` | `list[Edge]` | Yes | All edges in the graph |

### Example graph.yaml fragment

```yaml
schema_version: "1.0"
generated_at: "2026-04-13T10:00:00+00:00"
generated_by: "drg-migration-v1"

nodes:
  - urn: "directive:DIRECTIVE_001"
    kind: directive
    label: "Architectural Integrity Standard"
  - urn: "tactic:adr-drafting-workflow"
    kind: tactic
    label: "ADR Drafting Workflow"
  - urn: "action:software-dev/specify"
    kind: action
    label: "Specify (software-dev)"

edges:
  - source: "directive:DIRECTIVE_001"
    target: "tactic:adr-drafting-workflow"
    relation: requires
  - source: "directive:DIRECTIVE_001"
    target: "tactic:premortem-risk-identification"
    relation: requires
  - source: "action:software-dev/specify"
    target: "directive:DIRECTIVE_010"
    relation: scope
  - source: "action:software-dev/specify"
    target: "directive:DIRECTIVE_003"
    relation: scope
  - source: "action:software-dev/specify"
    target: "tactic:requirements-validation-workflow"
    relation: scope
  - source: "paradigm:domain-driven-design"
    target: "paradigm:anemic-domain-model"
    relation: replaces
    reason: >
      Anemic Domain Models strip behaviour from domain objects, reducing them
      to data bags with external procedural services.
```

## Validation Rules

The Pydantic model enforces these constraints at load time:

1. **URN format**: Every `urn`, `source`, and `target` must match `^[a-z_]+:[A-Za-z0-9_/.-]+$`
2. **Node kind consistency**: The `kind` field in a node must match the kind prefix in its `urn`
3. **No dangling references**: Every `source` and `target` in edges must reference a node that exists in `nodes`
4. **No unknown relations**: Every `relation` must be a valid `Relation` enum value
5. **No cycles in `requires`**: The subgraph of `requires` edges must be a DAG (detected via DFS)
6. **No duplicate edges**: The `(source, target, relation)` triple must be unique

## Layer Merging

The DRG supports two layers:

- **Shipped layer**: `src/doctrine/graph.yaml` (committed, generated by migration)
- **Project layer**: `{repo_root}/.kittify/doctrine/graph.yaml` (project-local overrides, optional)

Merge semantics:

1. Start with all nodes and edges from the shipped layer
2. Add all nodes from the project layer (new URNs are added; existing URNs keep the project-layer label)
3. Add all edges from the project layer (additive; no edge deletion)
4. Re-validate the merged graph (dangling refs, cycles, etc.)

The project layer is additive-only. It cannot remove shipped nodes or edges. Phase 2+ may introduce edge removal or override semantics.

## Query Semantics (for build_context_v2)

Given `(profile, action, depth)`:

1. **Resolve action node**: `action:{mission}/{action}` (e.g., `action:software-dev/implement`)
2. **Walk scope edges** (depth 1): Collect all nodes reachable from the action node via `scope` edges. These are the action's directly-scoped artifacts.
3. **Walk requires edges** (transitive): For each scoped artifact, walk `requires` edges until exhausted. These are hard dependencies.
4. **Walk suggests edges** (depth-limited): For each scoped artifact, walk `suggests` edges to `depth` hops. These are soft recommendations.
5. **Walk vocabulary edges** (depth 1): For each resolved node, collect `vocabulary` edges. These define glossary injection scopes.
6. **Deduplicate**: Union all resolved node URNs. Each artifact appears once.
7. **Materialize**: Load each resolved artifact via `DoctrineService` and render into the prompt block.

The profile dimension is reserved for Phase 4. In Phase 0, profile does not alter the graph query. The invariant test documents this as a known degenerate dimension.

## Accepted-Differences Manifest

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `str` | Yes | `"1.0"` |
| `entries` | `list[Entry]` | Yes | Empty by default |

### Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile` | `str` | Yes | Agent profile ID |
| `action` | `str` | Yes | Action name |
| `depth` | `int` | Yes | Depth parameter |
| `legacy_artifacts` | `list[str]` | Yes | URNs from legacy path |
| `drg_artifacts` | `list[str]` | Yes | URNs from DRG path |
| `reason` | `str` | Yes | Concrete justification (not "expected drift") |
| `follow_up_issue` | `str \| null` | Yes | GitHub issue number or null |
| `accepted_by` | `str` | Yes | Reviewer who accepted |
| `accepted_at` | `str` | Yes | ISO 8601 date |
