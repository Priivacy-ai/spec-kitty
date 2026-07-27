# Phase 1 Data Model: Doctrine Tension as First-Class DRG Edges

Grounded in the current state of `src/doctrine/drg/models.py`, `src/charter/cascade.py`,
and `src/charter/consistency_check.py` (read 2026-07-21). Only additive changes are
listed — existing members/fields not mentioned here are untouched.

## `Relation` (StrEnum) — `src/doctrine/drg/models.py`

Current members: `REQUIRES`, `SUGGESTS`, `APPLIES`, `SCOPE`, `VOCABULARY`,
`INSTANTIATES`, `REPLACES`, `DELEGATES_TO`, `SPECIALIZES_FROM`, `ENHANCES`,
`OVERRIDES`, `REFINES`.

**Add**:

| Member | Value | Semantics |
|---|---|---|
| `IN_TENSION_WITH` | `"in_tension_with"` | Symmetric, non-transitive. Two co-valid, co-activatable artefacts compete. Stored as ONE canonical edge — source = lexicographically-smaller URN (C-002) — queried from both endpoints via `edges_from`/`edges_to`. |
| `RECONCILES_TENSION` | `"reconciles_tension"` | Directional, active-artefact → one side of a tension pair. A pair is resolved only when an active artefact has this edge to BOTH sides (FR-002). |
| `REJECTS` | `"rejects"` | Directional, artefact → anti-pattern/smell node. Distinct from `IN_TENSION_WITH` (not symmetric — a good pattern rejects a bad one, they do not compete as equals) and from `REPLACES`/supersession. |

All three are **excluded** from `src/charter/cascade.py::REFERENCE_RELATIONS`
(currently `frozenset({Relation.REQUIRES, Relation.SUGGESTS, Relation.REFINES})`) —
by omission, not by adding a denylist check. FR-013's regression test asserts
`{IN_TENSION_WITH, RECONCILES_TENSION, REJECTS} & REFERENCE_RELATIONS == frozenset()`.

## Relation-description registry (new)

A single `Relation -> str` mapping — the one seam feeding both a future
`describe(relation)` call site and the FR-012 doc-parity check. Scope for this
mission: the three new relations only (Assumption A2; backfilling the other 12 is an
explicit non-goal). Lives alongside the `Relation` enum in
`src/doctrine/drg/models.py` (single canonical authority — do not duplicate the
mapping in the docs-parity check module; the check *reads* this registry).

```python
RELATION_DESCRIPTIONS: dict[Relation, str] = {
    Relation.IN_TENSION_WITH: "...",       # matches docs/architecture/doctrine-relationships.md verbatim
    Relation.RECONCILES_TENSION: "...",
    Relation.REJECTS: "...",
}
```

## `NodeKind` (StrEnum) — `src/doctrine/drg/models.py`

Current members: `DIRECTIVE`, `TACTIC`, `PARADIGM`, `STYLEGUIDE`, `TOOLGUIDE`,
`PROCEDURE`, `AGENT_PROFILE`, `MISSION_STEP_CONTRACT`, `TEMPLATE`, `ASSET`, `ACTION`,
`GLOSSARY_SCOPE`, `GLOSSARY`, `MISSION_TYPE`.

**Add**: `ANTI_PATTERN = "anti_pattern"` (D2). URN prefix `anti_pattern:<id>`.

D2's "smell" alias from spec.md is folded into a single enum member
(`ANTI_PATTERN`) with `tags: ["smell"]` available for finer marking, rather than two
enum members for one concept — avoids a `NodeKind` split where `DRGNode.tags` already
covers the finer distinction (see below).

**Ripple points** (all four must move together, per IC-01's risk note):

- `ArtifactKind` (`src/doctrine/artifact_kinds.py`) — add the corresponding member.
- `_SINGULAR_TO_PLURAL`, `_SINGULAR_TO_PER_KIND_FIELD` (wherever `ArtifactKind` maps to
  activation-config field names) — add the anti-pattern entry.
- Activation filter `_node_is_activated` — anti-pattern nodes must be excluded from
  normal activation cascading (an anti-pattern is referenced by `rejects`, never
  activated as a live rule).
- Cascade `_kind_of` (`src/charter/cascade.py`) — recognize the new `ArtifactKind`
  value so exclusivity computation (`deactivation_plan`) does not mis-bucket it.

## `DRGNode` — `src/doctrine/drg/models.py`

Current fields: `urn: str`, `kind: NodeKind`, `label: str | None`,
`provenance: str | None`.

**Add**: `tags: list[str] = Field(default_factory=list)`.

Required because Pydantic v2 defaults to `extra="ignore"` — an un-modelled YAML key
is silently dropped on load. Without this field, a hand-authored `tags: [anti-pattern]`
marker in a graph fragment would round-trip to nothing. `tags` is the home for
finer-grained marking (e.g. `smell` vs `anti-pattern`) within the single
`ANTI_PATTERN` `NodeKind`.

## `rejects`-target validation — `src/doctrine/drg/validator.py`

New validation rule (INV-004): a `DRGEdge` with `relation == Relation.REJECTS` MUST
have a `target` node whose `kind == NodeKind.ANTI_PATTERN` (or, if using the tags
approach for `smell`, `"smell" in target.tags`). Violation is a validation error, not
a warning — `rejects` at an unmarked node is a spec-defined error case (Edge Cases:
"`rejects` at an unmarked node").

## `ConsistencyReport` — `src/charter/consistency_check.py`

Current fields include `coherent: bool`, `unknown_references`,
`missing_from_doctrine`, `kind_violations`, `reference_id_divergences`,
`graph_kind_gaps` (and others — see module docstring).

**Add**: `unreconciled_tensions: list[TensionFinding]` (new dataclass/model, see below).
**Explicitly excluded** from the `coherent` boolean reduction (NFR-001: advisory,
never hard-blocks). DRG load for this specific check fails closed into
`verification_errors` — an exception during the tension scan must surface as a
verification error, never be swallowed into an empty/absent finding list (FR-009).

### `TensionFinding` (new)

```python
@dataclass(frozen=True)
class TensionFinding:
    pair: tuple[str, str]           # sorted URN pair — dedup key (Edge Case: symmetric authoring drift)
    resolution_paths: tuple[str, str] = (
        "deactivate one side",
        "activate a reconciler",
    )
```

One finding per unreconciled, co-activated `in_tension_with` pair — keyed on the
sorted URN pair so `(A,B)` and `(B,A)` authored independently dedupe to one finding
(Edge Case: symmetric authoring drift). Both resolution-path strings are always
present (SC-001 — a finding naming only one path fails the success criterion).

## `charter activate` warning (new)

Reuses `TensionFinding` (or a thin projection of it) surfaced alongside existing
activation warnings — same pair + resolution-path shape as the consistency-check
finding, so an operator sees one consistent vocabulary in both surfaces (FR-010,
SC-001).

## Orphan-lint (existing module, modified)

**Remove**: the `governs` (directive) and `supersedes` (adr) branches from the
orphan-lint rule set, and their references in the module docstring — neither is a
`Relation` enum member (verified: `Relation` has no `GOVERNS`/`SUPERSEDES`), so these
branches were dead/phantom logic producing false-positive `orphaned_directive`
findings on every built-in directive (FR-008, closes #2737).

## Built-in reconciliation directive (new content, not a schema change)

`reconcile-change-scope-tensions.directive.yaml` — a new built-in directive with
`reconciles_tension` edges to `directive:024-locality-of-change`,
`directive:025-boy-scout-rule`, and
`tactic:change-apply-smallest-viable-diff`. Its body carries the guidance for weighing
the tension pairs (FR-011). This is authored content (IC-02), not a model/schema
change — listed here because SC-002's live assertion (removing this directive makes
the findings reappear) depends on its edges being exactly these three, no more, no
fewer.
