# Data Model: Kind-Complete Cascade + Orphan Wiring (M5)

This mission is graph-logic + graph-data only; there are no new persistent
entities. The "data model" is the set of relation/kind sets and orphan
dispositions the change reshapes.

## Cascade followed-relation set (`charter.cascade.REFERENCE_RELATIONS`)

| Relation | Followed before | Followed after | Note |
|---|---|---|---|
| `requires` | ✓ | ✓ | hard dependency |
| `suggests` | ✓ | ✓ | soft recommendation |
| `refines` | ✓ | ✓ | refinement (#2079) |
| `scope` | ✗ | **✓ (new)** | action → governance artifacts (the #2829 fix) |
| `instantiates` | ✗ | **✓ (new)** | action → template (surfaces templates; filtered by the candidate filter) |
| `vocabulary` | ✗ | ✗ | targets `glossary_scope` (non-artifact); inert for cascade |
| `applies` | ✗ | ✗ | dead relation, nothing traverses it |
| `replaces` | ✗ | ✗ | supersession |
| `delegates_to` | ✗ | ✗ | runtime handoff |
| `specializes_from` | ✗ | ✗ | static lineage |
| `enhances` / `overrides` | ✗ | ✗ | pack overlay |
| `in_tension_with` | ✗ | ✗ | co-valid competitor |
| `reconciles_tension` | ✗ | ✗ | tension resolution |
| `rejects` | ✗ | ✗ | points at anti-pattern nodes |

Invariant: this set feeds **both** `_forward_reference_closure` (activation) and
`deactivation_plan` exclusivity. The expansion is symmetric; excluded relations
stay excluded in both directions.

## Cascade candidate filter (`_referenced_artifacts`)

- **Before**: keep every reached node for which `_kind_of(urn) is not None`
  (i.e. any `ArtifactKind`, including `template`/`asset`).
- **After**: additionally keep only kinds ∈
  `doctrine.artifact_kinds.CHARTER_ACTIVATABLE_KINDS`
  (`frozenset(ArtifactKind) - {TEMPLATE, ASSET}`; 10 kinds incl. `anti_pattern`).
- Traversal (which edges the BFS follows) and candidacy (which reached nodes are
  proposed) are **separate** concerns: `instantiates` is followed so the closure
  passes through actions, but `template` targets are dropped at candidacy.

## Orphan dispositions

| Artifact URN | Before | After | Mechanism |
|---|---|---|---|
| `styleguide:given-when-then-authoring` | `_ACTIVATED_BUT_ORPHANED` + `_ORPHANS_RESOLVED_BY_OVERLAY` | reachable, pure-graph edge | DIRECTIVE_034 frontmatter `suggests` (promoted) |
| `toolguide:gherkin` | `_ACTIVATED_BUT_ORPHANED` + `_ORPHANS_RESOLVED_BY_OVERLAY` | reachable, pure-graph edge | DIRECTIVE_034 frontmatter `suggests` (promoted) |
| `toolguide:sonar` | `_ACTIVATED_BUT_ORPHANED` + `_ORPHANS_RESOLVED_BY_OVERLAY` | reachable, pure-graph edge | DIRECTIVE_030 frontmatter `suggests` (promoted) |
| `styleguide:quadruple-a-test-format` | `_ACTIVATED_BUT_ORPHANED` + `_ORPHANS_RESOLVED_BY_OVERLAY` | pure-graph edge (still `_PROFILE_RESCUES`; 041 not action-scoped) | DIRECTIVE_041 frontmatter `suggests` (promoted) |
| `styleguide:deployable-skill-authoring` | `_ACTIVATED_BUT_ORPHANED` (sole source-less member) | direct-activation-only | new documented disposition + rationale |

Net ledger movement (IC-02, applied once):
- `_ACTIVATED_BUT_ORPHANED`: −5.
- `_ORPHANS_RESOLVED_BY_OVERLAY`: −4.
- new direct-activation-only disposition: +1 (`deployable-skill-authoring`).
- Shipped graph `(source, target, relation)` edge set: **unchanged** (promotions
  are lossless; overlay edge removed, identical frontmatter edge added).
- Node count: unchanged (no node added/removed).
- Reachability pins (`_ACTION_UNREACHABLE_D1/D2`, `_PROFILE_UNREACHABLE`,
  `_PROFILE_RESCUES`): unchanged (shipped graph identical).

## Edge metadata (directive frontmatter references)

- Directive `references` entries: `{type, id, when?}` today → `{type, id, when?,
  reason?}` after the symmetric `reason` add. Backward-compatible: no shipped
  directive ref carries `reason` today, so every existing edge is unchanged.
- The 4 promoted refs copy the overlay's `when` and `reason` verbatim so the
  regenerated edge is byte-identical.

## Ledger surfaces (re-ledgered once, IC-02)

- `tests/doctrine/drg/migration/test_extractor_projection.py` — orphan sets.
- `tests/doctrine/drg/test_reachability.py` — reachability pins + the new
  direct-activation-only record; totality/disjointness companion guard.
- `docs/plans/doctrine/delivery-reachability-wiring-table.md` — the 5 orphans'
  ledger rows.
