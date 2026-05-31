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
`src/doctrine/missions/mission_step_repository.py:43` has `if TYPE_CHECKING: from charter.pack_context import PackContext`. This violates the `doctrine ← charter` isolation rule (pytestarch follows TYPE_CHECKING imports).

Correct fix (per FR-020):
1. Define a narrow `ProjectContextProtocol` in `src/doctrine/missions/` matching only the fields `MissionStepRepository` actually uses (likely `activated_mission_step_contracts` and `activated_mission_types` — verify at implementation time).
2. Replace the `PackContext` annotation in `mission_step_repository.py` method signatures with `ProjectContextProtocol`.
3. Remove the `TYPE_CHECKING` import block entirely.

`ProjectContext` (from `src/charter/invocation_context.py`) satisfies the protocol structurally — no changes to `ProjectContext` needed. Pytestarch sees no charter import; mypy strict sees a defined protocol — both are satisfied.

Do NOT use a bare string literal annotation (`"PackContext"`) as the fix. With `from __future__ import annotations` active, all annotations are already lazy strings at runtime — the `TYPE_CHECKING` guard exists specifically for mypy. Removing it without a protocol replacement causes `error: Name "PackContext" is not defined [name-defined]` under mypy strict.

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
detect():   project has .kittify/ AND no activated_directives in config.yaml
            (presence of the new per-kind keys signals the migration has already run)
can_apply(): detect() returns True

apply():
  if .kittify/charter/charter.md exists:
    backup to .kittify/charter/backups/charter-{timestamp}.md
    warn user: "Existing charter backed up. Defaults merged. Review recommended."
  
  read src/charter/packs/default.yaml
  write ALL of the following to config.yaml (round-trip, comment-preserving):
    activated_kinds          ← from default pack (8-element set of plural kind names)
    mission_type_activations ← from default pack (all built-in mission type IDs)
    activated_directives     ← all built-in directive IDs from default pack
    activated_tactics        ← all built-in tactic IDs from default pack
    activated_styleguides    ← all built-in styleguide IDs from default pack
    activated_toolguides     ← all built-in toolguide IDs from default pack
    activated_paradigms      ← all built-in paradigm IDs from default pack
    activated_procedures     ← all built-in procedure IDs from default pack
    activated_agent_profiles ← all built-in agent profile IDs from default pack
    activated_mission_step_contracts ← all built-in MSC IDs from default pack
  
  inform user: "Default charter pack written. All built-in artifacts activated."
```

The default pack values come from `src/charter/packs/default.yaml` (new file). The migration reads it at runtime (not hardcoded inline) so it stays in sync with any future updates to the shipped pack.

**After migration, no per-kind field is `None`.** Every kind has an explicit activation frozenset populated from the default pack. The `None` = all-built-ins fallback applies only to pre-migration projects that have not yet run `spec-kitty upgrade`. Post-upgrade, the hard-restriction model is fully active for all kinds.

**Empty-set state post-upgrade**: A per-kind field can become `frozenset()` only through explicit user action (`charter deactivate` until the set is empty, or manual config.yaml edit). This is a valid intentional state meaning "nothing available for this kind." It is not the same as `None` (absent key). The default pack is the guarantee that users do not accidentally enter this state.

### Alternatives Considered
- **Write a new charter.md from scratch**: Too destructive for existing users with customizations. Rejected.
- **Separate `.kittify/charter/pack.yaml` activation file**: Unnecessary added format; config.yaml already handles it. Rejected.
