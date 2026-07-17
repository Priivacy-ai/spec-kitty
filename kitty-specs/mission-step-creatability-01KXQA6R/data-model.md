# Data Model — Mission-Type Creatability (S-C)

Schema + graph deltas. No database; entities are doctrine models + DRG nodes/edges.

## Entity changes

### `MissionType` (`src/doctrine/missions/models.py`)
- **Change**: **remove** the `template_set: dict[str, str] | None` field. `MissionType` is `frozen, extra="forbid"` — after removal, any YAML authoring `template_set:` fails validation (the loud-fail, SC-002).
- **Retained**: `schema_version`, `id`, `display_name`, `extends`, `action_sequence` (unchanged — `action_sequence` symmetry deferred to #2751).
- **Invariant**: no `.steps` attribute — steps resolve separately via `MissionStepRepository`.

### `MissionStep` / `MissionStepTemplateRef` (`models.py:87`, `:90-105`)
- **Unchanged shape**; newly *populated* for the 3 types: `template: MissionStepTemplateRef(artifact_key, template_file)`.
- **Authoring contract (C-003 / DD-03)**: `artifact_key ∈ {"spec", "plan"}` (shared runtime vocabulary — `"spec"` for creation, `"plan"` for `/plan`-setup); `template_file` per-type-unique (NFR-006).
- **Ordering (FR-011)**: steps are ordered by `sequence_index` at the projection source (deterministic).

### `template_set` projection (`step_projection.py:88`)
- **Producer**: `project_template_set(steps) -> dict[artifact_key, template_file] | None` — now the *only* source (no persisted field, no raw-YAML fallback).
- **Consumers**: `_resolve_template_set_slot` (`mission_type_profiles.py:744`, cached per `(mission_type, pack_context)`) → `ResolvedMissionType.template_set` (`@cached_property`, name retained per C-006) → `resolve_configured_template` (`resolver.py:395`, signature unchanged).

## DRG graph delta (Concern C)

### New nodes
- `template:<mission>/<file>` (kind `TEMPLATE`) via `template_catalog.template_urn` — one per authored/existing step `template` ref. software-dev contributes 2 (`template:software-dev/spec-template.md`, `template:software-dev/plan-template.md`).
- **Distinct from** the 16 bare `template:<name>` exemplars (#2712), which stay untouched (`template.graph.yaml`, `edges:[]`).

### New edges
- `action:<type>/<step> --instantiates--> template:<type>/<file>` (`Relation.INSTANTIATES`), **action-sourced** → land in `action.graph.yaml`.

### Counts (NFR-002)
- **N** = every step carrying a `template` ref across all four types (software-dev's 2 included). **N is computed at the end of authoring** (derived from FR-007), never pinned upfront.
- Node delta = edge delta = **N**. `_EXPECTED_NODE_COUNT` 280 → `280+N`; `_EXPECTED_EDGE_COUNT` 757 → `757+N`.
- **Orphans stay 10** (each new template node has an `instantiates` in-edge; the source `action:` node already exists). Ceiling 14 untouched.

## State / lifecycle
- No new state machine. The only lifecycle effect: the 3 types transition from *uncreatable* (`template_set` projects `None` → `TemplateConfigurationError`) to *creatable* (non-null projection) once their steps carry `artifact_key:"spec"` refs.
