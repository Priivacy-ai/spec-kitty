# Contract: `resolve_transitive_refs()`

**Location**: `src/doctrine/drg/query.py`
**Introduced in**: WP03
**Replaces**: `src/charter/reference_resolver.py :: resolve_references_transitively()` (deleted in same WP)
**Plan reference**: D-2 in plan.md

> **Amendment 2026-04-14**: This contract was rewritten after an internal review caught that the
> earlier draft used fabricated API surfaces. The live DRG API uses `DRGGraph` (not `MergedGraph`),
> a typed `Relation` enum with values `requires/suggests/applies/scope/vocabulary/instantiates/replaces/delegates_to`
> (not `uses`/`references`), and the shipped traversal primitive is
> `walk_edges(graph, start_urns, relations, max_depth)`. The contract below is the corrected version.

---

## Purpose

Walk the Doctrine Reference Graph (DRG) from a set of starting URNs and return the transitive closure of reachable artifacts, grouped by `NodeKind`. Functionally equivalent to the legacy `resolve_references_transitively()` in bucketed return shape so that callers (`src/charter/resolver.py`, `src/charter/compiler.py`, and their `src/specify_cli/charter/*` twins) swap one import line and adapt one call-site pattern.

## Relationship to existing DRG primitives

- `doctrine.drg.models.DRGGraph` — top-level graph document (shipped or merged). Input type.
- `doctrine.drg.models.NodeKind` — enum of 9 node kinds.
- `doctrine.drg.models.Relation` — enum of 8 typed relations.
- `doctrine.drg.loader.load_graph(path)` → `DRGGraph`.
- `doctrine.drg.loader.merge_layers(shipped, project)` → `DRGGraph` — shipped ∪ project overlay. **Returns `DRGGraph`, not a separate `MergedGraph` type.**
- `doctrine.drg.validator.assert_valid(graph: DRGGraph)` — rejects dangling edges, duplicate edges, `requires` cycles. Must have been called before `resolve_transitive_refs()`.
- `doctrine.drg.query.walk_edges(graph, start_urns, relations, max_depth)` → `set[str]` — the generic BFS primitive. `resolve_transitive_refs()` is a thin bucketing wrapper on top of `walk_edges`.

## URN addressing

The DRG uses URNs (`<kind>:<id>`) throughout — e.g. `directive:001-architectural-integrity-standard`, `tactic:situational-assessment`, `action:software-dev/implement`. Start URNs, visited URNs, and graph nodes are all URN-typed. Legacy `ResolvedReferenceGraph` used bare IDs (no `kind:` prefix); the new function bucket-groups by `NodeKind` and returns **bare IDs** in each per-kind list so callers need minimal adaptation.

## Signature

```python
from dataclasses import dataclass, field
from doctrine.drg.models import DRGGraph, Relation


@dataclass(frozen=True)
class ResolveTransitiveRefsResult:
    """Transitive closure of doctrine artifacts reachable from a set of starting URNs,
    bucketed by NodeKind.

    Field values are bare IDs (URN without the "<kind>:" prefix), preserving the
    legacy ResolvedReferenceGraph field shape for caller compatibility.
    """

    directives: list[str] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    paradigms: list[str] = field(default_factory=list)
    styleguides: list[str] = field(default_factory=list)
    toolguides: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    agent_profiles: list[str] = field(default_factory=list)
    # Edges whose target URN was not found in the graph (source_urn, target_urn).
    # Always [] when the input graph has passed assert_valid(), since the validator
    # rejects dangling targets at load time.
    unresolved: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True when all referenced artifacts were resolved (symmetric with legacy)."""
        return len(self.unresolved) == 0


def resolve_transitive_refs(
    graph: DRGGraph,
    *,
    start_urns: set[str],
    relations: set[Relation],
    max_depth: int | None = None,
) -> ResolveTransitiveRefsResult:
    """Walk `relations` edges from `start_urns` in `graph`, bucketing reachable nodes by NodeKind.

    A thin wrapper over :func:`walk_edges` that groups the flat result set by
    :class:`doctrine.drg.models.NodeKind` and strips the URN prefix from each
    per-kind list.  Designed as a behavior-equivalent replacement for the legacy
    :func:`charter.reference_resolver.resolve_references_transitively` during
    the Phase 1 cutover.

    Args:
        graph: The DRG graph to walk.  The graph MUST already have passed
            :func:`doctrine.drg.validator.assert_valid`; this function does not
            re-validate.
        start_urns: Seed URNs (e.g. ``"directive:001-architectural-integrity-standard"``).
            URNs whose ``<kind>:<id>`` prefix is not present in the graph are
            recorded in the returned ``unresolved`` field rather than raising.
        relations: Set of :class:`Relation` values to follow.  For legacy
            parity in the charter compiler / resolver, callers pass
            ``{Relation.REQUIRES, Relation.SUGGESTS}``; see R-2 below.
        max_depth: Forwarded to :func:`walk_edges`.  ``None`` = transitive closure.

    Returns:
        :class:`ResolveTransitiveRefsResult` with per-kind bucketed bare IDs.
        Each per-kind list is sorted lexicographically for deterministic output.

    Raises:
        Nothing.  Cycles in `requires` edges are already rejected by
        :func:`assert_valid` at load time.  Cycles in other relation kinds
        are handled by the BFS visited-set in :func:`walk_edges` (no-op
        convergence).
    """
```

## Traversal semantics

- Uses `walk_edges(graph, start_urns, relations, max_depth)` verbatim — no custom DFS.
- BFS with a visited set (cycle-safe convergence by construction of `walk_edges`).
- **Cycle behavior**: `requires` cycles are rejected at load time by `assert_valid`. Cycles in `suggests` / `applies` / other relations are benign under BFS-with-visited-set. The function does **not** raise `DoctrineResolutionCycleError`; the legacy resolver's cycle-raising semantics are relocated to the DRG validator layer.
- **Result bucketing**: after `walk_edges` returns a flat `set[str]` of URNs, iterate and look up each URN's node in `graph` (via `graph.get_node`). Dispatch by `NodeKind` into the corresponding list. Strip the `<kind>:` prefix when writing into the bucket.
- **Unresolved**: any URN returned by `walk_edges` that cannot be looked up in `graph` (shouldn't happen post-`assert_valid`, but defensively tracked) is appended to `unresolved` as `(source_urn_representative, target_urn)`. For a validated graph, `unresolved` is always `[]`.
- **Determinism**: sort each per-kind list lexicographically before returning.

## Behavioral-equivalence contract

For legacy parity during the cutover (T013/T015 of WP03), callers use `{Relation.REQUIRES, Relation.SUGGESTS}` — these are the two relation kinds that the Phase 0 migration extractor used when translating inline `tactic_refs` / `paradigm_refs` into DRG edges. The equivalence test in `tests/doctrine/drg/test_resolve_transitive_refs.py` must prove:

```python
# For every shipped directive that carried inline tactic_refs on pre-WP02 main
legacy = resolve_references_transitively([directive_id], doctrine_service)
drg = resolve_transitive_refs(
    graph,
    start_urns={f"directive:{directive_id}"},
    relations={Relation.REQUIRES, Relation.SUGGESTS},
)

assert sorted(legacy.directives) == sorted(drg.directives)
assert sorted(legacy.tactics) == sorted(drg.tactics)
assert sorted(legacy.styleguides) == sorted(drg.styleguides)
assert sorted(legacy.toolguides) == sorted(drg.toolguides)
assert sorted(legacy.procedures) == sorted(drg.procedures)
assert legacy.is_complete == drg.is_complete
```

The relation set that preserves parity (`{REQUIRES, SUGGESTS}`) is the authoritative answer from Phase 0's migration extractor. If equivalence fails for any shipped directive, the failure mode is either:

- The migration extractor did not map every inline reference to a `requires` or `suggests` edge (Phase 0 calibration gap — escalate per research.md R-2), OR
- The caller chose the wrong relation set (fix the caller, not the helper).

## Caller-side wiring

### Before (pre-WP03, still in src/ during WP02)

```python
# src/charter/resolver.py
from charter.reference_resolver import resolve_references_transitively
...
graph = resolve_references_transitively(starting_directive_ids, doctrine_service)
# graph.directives, graph.tactics, ..., graph.unresolved
```

### After (WP03, T015)

```python
# src/charter/resolver.py
from pathlib import Path
from charter.catalog import resolve_doctrine_root
from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import Relation
from doctrine.drg.query import resolve_transitive_refs
from doctrine.drg.validator import assert_valid

...

def _load_validated_graph(repo_root: Path):
    """Helper: load shipped+project merged DRG and validate."""
    doctrine_root = resolve_doctrine_root()
    shipped = load_graph(doctrine_root / "graph.yaml")
    project_graph_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
    project = load_graph(project_graph_path) if project_graph_path.exists() else None
    merged = merge_layers(shipped, project)
    assert_valid(merged)
    return merged


# At each former call site of resolve_references_transitively:
graph_obj = _load_validated_graph(repo_root)
start_urns = {f"directive:{d}" for d in starting_directive_ids}
graph = resolve_transitive_refs(
    graph_obj,
    start_urns=start_urns,
    relations={Relation.REQUIRES, Relation.SUGGESTS},
)
# graph.directives, graph.tactics, ..., graph.unresolved — same field shape as legacy
```

The `_load_validated_graph` helper goes into `src/charter/_drg_helpers.py` (new module) so `resolver.py` and `compiler.py` share it. Same pattern in `src/specify_cli/charter/_drg_helpers.py`.

## Non-goals

- **Not** a replacement for `resolve_context()`. That function is driven by an action URN and has its own 4-step algorithm (scope → requires → suggests → vocabulary). It stays as-is.
- **Not** a replacement for `walk_edges()`. That function is the base primitive; `resolve_transitive_refs()` is the bucketing sugar.
- **Not** a DRG redesign. `DRGGraph`, `NodeKind`, `Relation`, `merge_layers`, `assert_valid` are unchanged.
- **Not** a new cycle-detection mechanism. Cycle detection lives in `assert_valid()` for `requires` edges; other relations are allowed to have cycles (BFS converges).

## Testing

`tests/doctrine/drg/test_resolve_transitive_refs.py` must cover:

1. **Deterministic output**: same input → same output; lists are lexicographically sorted.
2. **Empty start set**: returns an empty `ResolveTransitiveRefsResult`.
3. **Unknown starting URN**: recorded in `unresolved` as `(start_urn, start_urn)` or similar; does not raise.
4. **Edge-kind filter**: a fixture with `{REQUIRES: A→B, SUGGESTS: A→C, SCOPE: A→D}` starting from `{A}` with `relations={REQUIRES}` returns only `B` (not `C` or `D`).
5. **Bucketing by kind**: given visited URNs of mixed kinds, each ID lands in the correct per-kind list; URN prefix is stripped.
6. **Behavioral equivalence**: for every shipped directive with inline `tactic_refs:` on pre-WP02 state (captured as a golden fixture set), the legacy `resolve_references_transitively` and the new `resolve_transitive_refs({REQUIRES, SUGGESTS})` produce identical bucket-by-bucket output.
7. **max_depth forwarding**: a fixture where `max_depth=1` excludes depth-2 nodes; confirms the argument is forwarded correctly.

The legacy tests (`tests/charter/test_reference_resolver.py`, `tests/doctrine/test_cycle_detection.py`, `tests/doctrine/test_shipped_doctrine_cycle_free.py`) are deleted or rehomed **only after** the new suite is green and manually confirmed to subsume their coverage (per plan D-4, user-adjustment #3). Rehome plan for those tests is in WP03's T018 subtask.
