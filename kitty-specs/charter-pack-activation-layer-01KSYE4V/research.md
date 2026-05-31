# Research: Charter Pack Activation Layer

**Date**: 2026-05-31  
**Mission**: charter-pack-activation-layer-01KSYE4V  
**Branch**: pr/charter-doctrine-mission-type-configuration

---

## 1. Activation State Storage

### Decision
Write activation state changes directly to `.kittify/config.yaml` under the `activated_kinds` and `mission_type_activations` keys. Retire the override-files write path for activation state.

### Rationale
`PackContext.from_config()` (`src/charter/pack_context.py:112`) reads exclusively from `.kittify/config.yaml`. The Phase 1 `charter activate mission-type` implementation writes to `.kittify/overrides/mission-types/<id>.yaml`, which `PackContext` never reads. There is no code path that syncs override files back into config.yaml. The gap is architectural: two write paths with only one read path. Consolidating to config.yaml is the minimal fix.

### Reader Gap Root Cause
- `charter_activate.py:activate_mission_type_override()` writes `.kittify/overrides/mission-types/<id>.yaml`
- `PackContext.from_config()` reads only `config.yaml:mission_type_activations`
- The override files are read by `resolve_action_sequence()` for step-sequence purposes, but `PackContext.activated_mission_types` is populated solely from config.yaml
- Fix: `charter activate <kind> <id>` should update `config.yaml` directly, not write separate override files

### How PackContext reads config.yaml
- `activated_kinds` key → frozenset of kind strings (falls back to all 8 built-in kinds if absent)
- `mission_type_activations` key → frozenset of mission type IDs (falls back to 4 built-in IDs if absent)
- Both keys use round-trip ruamel.yaml writes with `preserve_quotes=True`

### Alternatives Considered
- **Keep override files, make PackContext read them**: Increases complexity — two file formats for activation state. Rejected.
- **New separate activation state file**: Unnecessary; config.yaml already has the right structure and read logic. Rejected.

---

## 2. Resolution Pattern Wiring Map

Three patterns exist across the 9 activatable artifact kinds. All are currently **unfiltered** — `PackContext.activated_kinds` is populated but never consulted by any resolver.

### Pattern A: DRG-based (directive, tactic, styleguide, toolguide)

Resolved via `load_validated_graph()` → `resolve_context()` from `doctrine.drg.query`.  
`filter_graph_by_activation(graph, pack_context)` in `src/charter/drg.py:666` is fully implemented but has **zero production callers**.

| Call Site | File | Line | Fix |
|-----------|------|------|-----|
| `_load_action_doctrine_bundle()` | `src/charter/context.py` | 523 | Pass `pack_context`; call `filter_graph_by_activation(merged, pack_context)` before `resolve_context()` |
| `resolve_references_transitively()` | `src/charter/reference_resolver.py` | 40 | Pass `pack_context`; filter before `resolve_transitive_refs()` |
| `_resolve_transitive_reference_graph()` | `src/charter/compiler.py` | 499 | Pass `pack_context`; filter after load |
| `executor.py` step execution | `src/specify_cli/mission_step_contracts/executor.py` | 170 | Pass `pack_context`; filter before `resolve_context()` |

The `drg.py` inline comment block (lines 712–738) explicitly documents that `filter_graph_by_activation` is the FR-018 access point for runtime resolvers.

### Pattern B: Flat catalog (paradigm, procedure)

Resolved via `DoctrineService.paradigms` / `DoctrineService.procedures`. `DoctrineService` is constructed with built_in_root, org_roots, project_root — no `PackContext` plumbing.

| Call Site | File | Line | Fix |
|-----------|------|------|-----|
| `generate.py` charter generation | `src/specify_cli/cli/commands/charter/generate.py` | 47 | Construct `DoctrineService` with `pack_context`; filter in `.paradigms`/`.procedures` property |
| `org_layer.py` linter | `src/specify_cli/charter_runtime/lint/checks/org_layer.py` | 218, 236 | Add `pack_context` parameter |
| `load_org_charter_policies()` | `src/specify_cli/doctrine/org_charter.py` | 464 (signature), 660, 710 (callers) | Already has `pack_context` parameter; 3 production callers don't pass it |

### Pattern C: Direct repository (agent_profile, mission_step_contract)

`agent_profile` resolved via `DoctrineService.agent_profiles`. `mission_step_contract` resolved via `MissionStepRepository` (orphan — no production callers).

| Call Site | File | Line | Fix |
|-----------|------|------|-----|
| `DoctrineService` agent_profiles access | Multiple via `charter/resolver.py` | ~257 | Pass `pack_context` to `DoctrineService`; filter in `agent_profiles` property |
| `MissionStepRepository.resolve()` | `src/doctrine/missions/mission_step_repository.py` | 170 | Already has `pack_context` param; wire through `charter.mission_steps` facade |
| `charter.mission_steps` facade | `src/charter/mission_steps.py` | — | Add `MissionStepRepository` re-export |
| `load_org_charter_policies()` callers | `src/specify_cli/doctrine/org_charter.py` | 660, 710 | Pass `pack_context` to existing parameter |

---

## 3. `filter_graph_by_activation` Wiring

### Finding
`filter_graph_by_activation(graph: DRGGraph, pack_context: PackContext) -> DRGGraph` is:
- Fully implemented in `src/charter/drg.py:666`
- Exported in `__all__` at line 84
- Documented with a call-site contract at lines 712–738
- Has **zero non-test, non-`__all__` callers** in `src/`

### Confirmed Production Wiring Sites
Priority order (highest impact first):
1. `src/charter/context.py:523` — action doctrine bundle load → feeds directive/tactic/styleguide/toolguide to prompt rendering
2. `src/charter/reference_resolver.py:40` — transitive reference resolution
3. `src/charter/compiler.py:499` — charter compilation
4. `src/specify_cli/mission_step_contracts/executor.py:170` — step contract execution

The DRG comment block explicitly names these callers as required (lines 712–738): "callers that need activation filtering MUST call filter_graph_by_activation explicitly."

---

## 4. `MissionStepRepository` Wiring

### Finding
`MissionStepRepository` in `src/doctrine/missions/mission_step_repository.py`:
- `default()` classmethod at line 162 — correct, PackContext-aware
- `resolve(mission_type_id, step_id, pack_context=None)` at line 170 — correct API
- `resolve_all_for_mission_type(mission_type_id, pack_context=None)` at line 213 — correct API
- Already accepts `PackContext` for org/project layer resolution

**`charter/mission_steps.py`** re-exports: `MissionStep`, `MissionStepContract`, `MissionStepContractRepository`, `MissionStepContractStep` — **NOT `MissionStepRepository`**. Zero callers in `src/charter/` or `src/specify_cli/`.

### Fix
1. Add `MissionStepRepository` to `charter/mission_steps.py` re-exports
2. Wire in the runtime path where action sequences drive step execution — `specify_cli/next/` or `charter/mission_type_profiles.py` should call `MissionStepRepository.default().resolve(mission_type_id, step_id, pack_context)` for org/project step overrides

### C-004 Fix
`src/doctrine/missions/mission_step_repository.py:43` has `if TYPE_CHECKING: from charter.pack_context import PackContext`. This violates the `doctrine ← charter` isolation rule (pytestarch follows TYPE_CHECKING imports). Fix: replace with a string literal annotation `"PackContext"` for the method signatures and remove the `TYPE_CHECKING` import entirely.

---

## 5. Upgrade Migration Design

### Hook Point
New migration: `src/specify_cli/upgrade/migrations/m_3_2_8_default_charter_pack.py`
- Naming follows `m_{semver_underscored}_{description}` pattern
- Registration via `@MigrationRegistry.register` (auto-discovered at import)
- `target_version = "3.2.8"`

### Backup Strategy
Existing charter migration (`m_3_2_6_charter_bundle_v2.py`) modifies in-place without backup. For the new migration touching an existing user charter, use:
```
.kittify/charter/backups/charter-{ISO_timestamp}.md
```
Pattern: copy before modify, emit Rich warning about the backup location, strongly advise review.

### ruamel.yaml Comment Preservation
Confirmed: `m_3_2_7_activate_builtin_mission_types.py` uses `YAML()` round-trip mode with `preserve_quotes=True`. The same pattern is safe for writing `activated_kinds` and `mission_type_activations` into config.yaml.

### Upgrade Algorithm
```
detect():   project has .kittify/ AND no activated_kinds in config.yaml
can_apply(): detect() returns True

apply():
  if .kittify/charter/charter.md exists:
    backup to .kittify/charter/backups/charter-{timestamp}.md
    warn user: "Existing charter backed up. Defaults merged. Review recommended."
    merge pack defaults into config.yaml activated_kinds / mission_type_activations
  else:
    write default pack values to config.yaml activated_kinds / mission_type_activations
    inform user: "Default charter pack written. All built-in artifacts activated."
```

The default pack values come from `src/charter/packs/default.yaml` (new file). The migration reads it at runtime (not hardcoded inline) so it stays in sync with any future updates to the shipped pack.

### Alternatives Considered
- **Write a new charter.md from scratch**: Too destructive for existing users with customizations. Rejected.
- **Separate `.kittify/charter/pack.yaml` activation file**: Unnecessary added format; config.yaml already handles it. Rejected.
