# Contract sketch: tension-arbiter annotation fields (WP02)

**Locations**: `src/charter/offering/drg/query.py` (`ResolvedContext`, `resolve_context`), `src/charter/action_doctrine_bundle.py` (`_ActionDoctrineBundle`, `_load_action_doctrine_bundle`)
**Introduced in**: WP02 (mission `governance-at-the-gate`)
**Spec reference**: FR-009, SC-008; NFR-003 (latency parity), NFR-004 (single source of truth, additive contract)

## Purpose

Surface `reconciles_tension` / `in_tension_with` DRG edges into the delivered
doctrine payload so a consumer of `ResolvedContext` or `_ActionDoctrineBundle`
can see, without a second query, which co-delivered tensions have an
arbitrating reconciler and which do not.

## Field shapes

Both fields are **additive, trailing, defaulted** on their respective frozen
dataclasses, and are **tuples, never `dict`/`list`** — a frozen dataclass's
auto-generated `__hash__` requires every field to be hashable, and both
`ResolvedContext` and `_ActionDoctrineBundle` are used in hashable contexts
(brownfield-verified constraint, tasks.md WP02 T2).

```python
tension_arbiters: tuple[tuple[str, tuple[str, ...]], ...] = ()
unarbitrated_tensions: tuple[tuple[str, str], ...] = ()
```

- **`tension_arbiters`** — one entry per reconciler that arbitrates at least
  one co-delivered tension pair, as `(arbiter_urn, arbitrated_urns)`.
  `arbitrated_urns` is the sorted tuple of every tension-pair endpoint that
  arbiter bridges (a reconciler that arbitrates more than one pair in scope
  collects all of them into one entry, not one entry per pair). Sorted by
  `arbiter_urn` for deterministic equality.

  Example (mirrors the real corpus:
  `packs/built-in/directives/reconcile-change-scope-tensions.directive.yaml` +
  the `RECONCILE_CHANGE_SCOPE_TENSIONS --reconciles_tension--> DIRECTIVE_024`
  / `DIRECTIVE_025` edges in
  `src/charter/offering/drg/migration/hand_authored_overlay.py`):

  ```python
  (
      ("directive:RECONCILE_CHANGE_SCOPE_TENSIONS",
       ("directive:DIRECTIVE_024", "directive:DIRECTIVE_025")),
  )
  ```

- **`unarbitrated_tensions`** — one `(source, target)` entry per co-delivered
  `in_tension_with` pair with no reconciler bridging BOTH sides. The pair
  ordering matches how `in_tension_with` is itself stored in the DRG
  (lexicographically-smaller URN as `source`, per `Relation`'s docstring in
  `models.py`), sorted for deterministic equality across the whole tuple.

  ```python
  (
      ("directive:DIRECTIVE_TENSION_A", "directive:DIRECTIVE_TENSION_B"),
  )
  ```

## Scope and reachability rules

- A tension pair counts as "in scope" only when **both** endpoints are
  members of the resolved artifact set (`ResolvedContext.artifact_urns` —
  scope + requires + suggests). `in_tension_with` is queried as a plain edge
  scan, not `edges_from`/`edges_to`, so it is seen regardless of which
  endpoint the graph stores as `source`.
- A reconciler counts as bridging a pair only when it carries a
  `reconciles_tension` edge to **both** sides (mirrors
  `consistency_check._tension_reconciled_urns`'s "half-reconciled pairs stay
  flagged" rule) — a single-sided edge leaves the pair in
  `unarbitrated_tensions`.
- **The reconciler itself need not be in the action's resolved scope** to
  arbitrate a pair that is (SC-008: "a delivered bundle ... carries its
  reconciler"). Only the tension pair's two endpoints must be delivered.

## Traversal semantics (NFR-003, NFR-004)

- `resolve_context` computes the annotation via `_tension_annotations(graph,
  all_artifacts)` — a single bounded pass over `graph.edges` filtered by
  relation, **not** a second `walk_edges` BFS. The common case (no
  `in_tension_with` edge touches the resolved scope) returns `((), ())`
  immediately after the first filter pass, so latency for a no-tension
  action is unchanged from before this field existed.
- `_load_action_doctrine_bundle` does no traversal of its own: it forwards
  `resolved.tension_arbiters` / `resolved.unarbitrated_tensions` verbatim
  onto the constructed `_ActionDoctrineBundle`.
- No versioned-contract bump — both dataclasses are designed for additive,
  defaulted-trailing-field extension (see the existing `bridge_urns`
  precedent on `_ActionDoctrineBundle`), so every pre-existing keyword
  construction site (`ResolvedContext(artifact_urns=..., glossary_scopes=...)`,
  the various `_ActionDoctrineBundle(mission=..., ...)` sites in
  `src/` and `tests/charter/`) stays valid byte-for-byte.

## Non-goals

- **Not** a change to `Relation.IN_TENSION_WITH` / `Relation.RECONCILES_TENSION`
  semantics — those are unchanged (`models.py`).
- **Not** a replacement for `consistency_check.scan_unreconciled_tensions`
  (WP01's gate-side finding). That function scans the *activation-filtered*
  DRG for a project-wide compliance report; this annotation scans the
  *action-resolved* scope for a single action's delivered payload. The two
  answer different questions over different node sets and are not required
  to agree pair-for-pair (an unreconciled pair the gate flags may not be
  co-delivered to any given action's scope, and vice versa).
- **Not** a new graph walk primitive. `_tension_annotations` reuses the
  `graph.edges` scan already at hand inside `resolve_context`, the same
  bounded-pass style `consistency_check._tension_candidate_pairs` /
  `_tension_reconciled_urns` already use for the gate-side finding.

## Testing

- `tests/doctrine/drg/test_tension_arbiters.py` — `resolve_context`-level
  coverage: reconciled pair maps to its arbiter, unreconciled pair surfaces
  in `unarbitrated_tensions`, symmetric-edge-direction independence,
  half-reconciled-stays-unarbitrated, arbiter-need-not-be-in-scope,
  no-tension-in-scope default, hashability, and backward-compatible
  positional construction.
- `tests/charter/test_action_bundle_tension_arbiters.py` — bundle-level
  propagation through the real `_load_action_doctrine_bundle` ->
  `resolve_context` wiring (hermetic, patched `load_validated_graph`), plus
  the typeless-mission empty-default path.
