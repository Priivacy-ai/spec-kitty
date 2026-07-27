# Phase 1 Data Model — DRG completeness (#2843)

This is a refactor/correctness mission, not a schema mission — no new persisted entities. The
"model" here is the small set of in-memory concepts whose *invariants* the mission fixes.

## Entities & invariants

### `Relation` (enum) + `RELATION_DESCRIPTIONS` (map) — `src/doctrine/drg/models.py`
- **Members**: 15 (`requires, suggests, refines, replaces, enhances, overrides, specializes_from, delegates_to, scope, instantiates, applies, vocabulary` + the 3 already described: `in_tension_with, reconciles_tension, rejects`).
- **Invariant (target)**: `set(RELATION_DESCRIPTIONS) == set(Relation)` and every value is a non-empty string (enforced by `tests/doctrine/drg/test_models.py`, converted from a `== {3}` pin).
- **Emission status** (drives the descriptions, not edges): `applies`=1 edge, `scope`=157 edges (contested — describe distinctly, `applies desc != scope desc`); `vocabulary`/`refines`/`delegates_to`=0 edges everywhere (dormant); `enhances`/`overrides`/`replaces`=0 in built-in **by design** (org-pack overlay relations). No edges are rewired (C-006).

### `PackContext.activated_<kind>` — `src/charter/pack_context.py`
- **Holds**: config **stems** (e.g. `001-architectural-integrity-standard`), three-state (`None` = default-allow; empty frozenset = allow-none; populated = allow-listed). **Unchanged by this mission** (the gate resolves at read time; the field stays stems).
- **Roots**: `PackContext` carries the doctrine/org roots the resolver needs (used at `consistency_check.py:940`).

### Activation gate — `charter/drg.py`
- **`_node_is_activated(kind, artifact_id, pack_context)`**: Step 2 kind-gate, Step 3 per-ID gate.
- **Invariant (target)**: Step 3 compares the node's canonical `artifact_id` against the activated set **after** resolving each activated stem→canonical via `resolve_artifact_urn` (roots from `pack_context`). `None` set → default-allow (unchanged). Populated set → a node survives iff its canonical id is among the resolved-canonical activated set.
- **Contract**: require-canonical — config stems are resolved; raw canonical-ids in config are not a supported input form (C-002).

## State transitions

None. The mission changes a *comparison predicate*, not any lifecycle/state machine.
