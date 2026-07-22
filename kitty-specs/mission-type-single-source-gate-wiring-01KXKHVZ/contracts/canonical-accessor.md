# Contract — Canonical mission-type accessor (IC-1a)

**Location:** doctrine layer, adjacent to `MissionTypeRepository`
(`src/doctrine/missions/mission_type_repository.py` or a sibling module).

## Interface

```python
@functools.cache
def builtin_mission_type_ids() -> tuple[str, ...]: ...       # sorted, cached
def builtin_mission_type_id_set() -> frozenset[str]: ...      # frozenset convenience
# builtin_mission_type_ids.cache_clear() is the test seam (auto-provided by functools.cache)
```

## Guarantees

1. **Single source.** Values derive from `MissionTypeRepository.default().ids()` (the `mission_types/*.yaml`
   tree). No hardcoded roster.
2. **Loud-fail transitivity.** If `MissionTypeRepository` raises on an id≠stem mismatch or invalid schema,
   the accessor raises (does not swallow).
3. **Caching.** ≤1 filesystem scan per process; repeated calls return identical, cheap results.
4. **Layer-clean.** Lives in doctrine; imports no `charter`/`specify_cli`. Charter consumers import it
   lazily inside functions **for import-time-I/O timing** (NFR-001) — NOT for cycle avoidance (there is no
   cycle: doctrine never imports charter; the `# noqa: PLC0415` guards in `action_grain.py` protect a
   *different*, intra-charter cycle).

## Test seam (C-010) — cache vs SC-001 synthetic-type test

A parameterless `@functools.cache` accessor bound to `MissionTypeRepository.default()` would otherwise make
the SC-001 "add a synthetic type → universal pickup" test impossible:
- writing the synthetic YAML to a **tmp dir** is invisible (no injection seam);
- writing to the **real bundled dir** is defeated by the cache AND races xdist workers (shared repo tree).

**Contract:** the SC-001 guard test monkeypatches the resolved default root to a tmp dir (or monkeypatches
`MissionTypeRepository.default`), then calls `builtin_mission_type_ids.cache_clear()` before asserting
pickup. The test MUST NOT mutate `src/doctrine/missions/mission_types/`. Production never adds/removes
built-in type YAMLs mid-process, so the cache is safe in production (NFR-002).

## Consumers (must all resolve through this contract)

- Roster A `CANONICAL_MISSION_TYPES` (`charter/mission_type_profiles.py`)
- Roster B `_BUILTIN_MISSION_TYPE_IDS` (`charter/pack_context.py`) — frozenset form
- Roster C migration (`m_3_2_0rc35_...`) — via `MissionTypeRepository.default().ids()` at apply()-time
- Roster D `ALLOWED_MISSION_TYPES` (`charter/activations.py`) — union `{any, generic}`
- Roster E `_MISSION_IDENTIFIER_ANSWERS` (`charter/synthesizer/interview_mapping.py`) — preserve `software_dev` alias

## Test obligations

- Adding a synthetic `mission_types/*.yaml` makes every roster reflect it (single-source guard, SC-001).
- Importing charter modules triggers zero accessor calls / zero `mission_types/` reads (SC-005 / NFR-001).
- Frozenset-equality contract of Roster B preserved.
