# Data Model — Mission-Type DRG Node + Cross-Grain Integrity

## Entity: `mission_type` DRG node (new)

| Field | Value | Notes |
|-------|-------|-------|
| `urn` | `mission_type:<type>` | e.g. `mission_type:software-dev`. New URN scheme (IC-01). |
| `kind` | `mission_type` | New node kind registered in `drg/models.py` + `validator.py`. |
| `label` | `<type>` | Human label (e.g. `software-dev`). |

- **Cardinality:** one node per built-in type in `missions/mission_types/*.yaml` (4 today).
- **Generation:** emitted by `drg/migration/extractor.py`; materialized into `graph.yaml`; freshness-gated by `regenerate-graph --check`.
- **Edges (this mission, minimal):** enough for cascade `_source_urn` resolution (IC-03). Full `uses`/`requires` edges to templates/step-contracts are S0 continuation (out of scope).

## Entity: `ResolvedGovernance` action-grain slot (behavioural change)

| Aspect | Before | After |
|--------|--------|-------|
| `action_grain` source | `_EMPTY_GRAIN` (stub, `:592`) | live union of per-action `ActionIndex`, adapted to `Mapping[str, list[str]]` (IC-07) |
| Materialization | eager at construction (`from_grains:590`) | **lazy thunk** (mirror `_expected_artifacts_thunk`), memoised (IC-06) |
| FR-013 guard fire-point | construction time | first `.governance` access (fast-fail; never on hot `.action_sequence`) |
| Root authority | n/a | **builtin root** `MissionTypeProfileRepository._default_built_in_dir()` (= `src/doctrine/missions`), reached via the resolver's existing `_mission_type_profile_repository(repo_root)` — NOT `repo_root`. Full project/org action-index **overlay symmetry** with the type-grain is a **tracked follow-up**, not deliverable via single-`Path` `load_action_index` (no project `actions/` override layout today). |

**Invariants:**
- I1 — activation gating outputs (`existing_mission_types`, `activated_mission_types`, action-sequence) byte-identical (C-001).
- I2 — hot `.action_sequence` path invokes zero `load_action_index` (NFR-001; spy-verified).
- I3 — cross-grain URN disjointness across all shipped (type × action) holds (gate IC-04); fails on the deliberate-collision fixture (IC-05).
- I4 — exactly one implementation of the type⊕action union exists in the tree (C-002; IC-08).

## Value object: `ActionIndex → Mapping` adapter (new pure helper, IC-07)

- Input: `ActionIndex` dataclass (`directives/tactics/paradigms/styleguides/toolguides/procedures/agent_profiles`).
- Output: `Mapping[str, list[str]]` keyed by governance kind, as `from_grains` expects.
- Pure, unit-tested; dedup delegated to `_merge_disjoint_grain`.

## Typing: `expected_artifacts` (IC-10)

- 3 sites (`:334` thunk, `:343` property, `:637` resolver) move from `object | None` to a `TypedDict`/type alias (doctrine-native mapping shape) — **not** a pydantic model that would cross the `charter → doctrine` boundary (C-001 layer rule).
