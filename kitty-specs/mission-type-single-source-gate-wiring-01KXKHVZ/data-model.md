# Data Model — Mission-Type Single-Source + Gate Wiring

This mission adds no persistent data. The "model" here is the set of in-code contracts (return shapes,
exception shapes, finding shapes) that the WPs must honor.

## E-1 — Canonical mission-type accessor (doctrine layer)

| Element | Shape | Notes |
|---------|-------|-------|
| `builtin_mission_type_ids()` | `tuple[str, ...]` | Sorted (lexicographic). Cached (`@functools.cache`). Derived from `MissionTypeRepository.default().ids()`. |
| frozenset convenience | `frozenset[str]` | Same members as the tuple; for membership/default consumers (Roster B, D base set). |

**Invariants:**
- Exactly one filesystem scan per process (NFR-002); repeated calls return identical results.
- Importing any `src/charter/*` module triggers zero calls to this accessor (NFR-001).
- Loud-fails transitively: if `MissionTypeRepository` raises (id≠stem / invalid schema), the accessor raises.

## E-2 — Roster derivations

| Roster | File | Container | Extra members preserved |
|--------|------|-----------|-------------------------|
| A `CANONICAL_MISSION_TYPES` | `charter/mission_type_profiles.py` | tuple/iterable | none |
| B `_BUILTIN_MISSION_TYPE_IDS` | `charter/pack_context.py` | **frozenset** | none |
| C `_BUILTIN_MISSION_TYPES` | `migrations/m_3_2_0rc35_...py` | list | none (live-read at apply()) |
| D `ALLOWED_MISSION_TYPES` | `charter/activations.py` | set/frozenset | `{any, generic}` sentinels |
| E `_MISSION_IDENTIFIER_ANSWERS` | `charter/synthesizer/interview_mapping.py` | mapping | `software_dev` underscore alias |

## E-3 — `ActionIndex` / `ActionIndexError`

| Element | Shape | Notes |
|---------|-------|-------|
| `ActionIndex` (existing) | frozen dataclass, 7 `list[str]` artifact-kind fields + `action` | Unchanged shape. |
| `ActionIndexError(ValueError)` (new) | co-located in `action_index.py` | Message: index path + offending key + found type. |

**`load_action_index` decision table:**

| Input state | Behavior |
|-------------|----------|
| File missing | Return `ActionIndex(action=action)` (silent fallback) — unchanged |
| File present, valid, empty content | Return empty-content `ActionIndex` — no raise |
| File present, non-mapping root | **raise `ActionIndexError`** |
| File present, artifact-kind field not a list (e.g. `directives: "x"`) | **raise `ActionIndexError`** |
| File present, unparseable YAML (`YAMLError`) | **raise `ActionIndexError`** |

## E-4 — Doctrine-health cross-grain finding (#2666)

| Element | Shape | Notes |
|---------|-------|-------|
| Cross-grain check result | folded into existing `DoctrineHealthReport` health + a `--json` finding entry | On `CrossGrainDoubleDeclarationError`: report unhealthy, RC=1, structured finding (mission type + colliding URN). On success: healthy, no exit-code change. |

## E-5 — `builtin_missions_root()` (#2668)

| Element | Shape | Notes |
|---------|-------|-------|
| `builtin_missions_root()` | `Path` → `src/doctrine/missions` | Public module-level accessor; classmethod `_default_built_in_dir` delegates (or is replaced). Replaces 2 `# noqa: SLF001` cross-class calls. |
