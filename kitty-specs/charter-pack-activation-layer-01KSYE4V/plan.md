# Implementation Plan: Charter Pack Activation Layer

**Branch**: `pr/charter-doctrine-mission-type-configuration` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)  
**Input**: `kitty-specs/charter-pack-activation-layer-01KSYE4V/spec.md`

## Summary

Complete the charter activation model across all 9 doctrine artifact kinds. Phase 1 delivered mission-type activation but left `filter_graph_by_activation` and `MissionStepRepository` as dead code, left `PackContext.activated_kinds` populated but never read, and broke 6 architectural tests. This mission wires the full activation layer (hard restriction, explicit cascade control), ships a default charter pack for backward compatibility, fixes all architectural test breakages, and adds a `charter pack consistency-check` command.

**Planning branch**: `pr/charter-doctrine-mission-type-configuration`  
**Merge target**: `pr/charter-doctrine-mission-type-configuration`

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic v2, pytest, mypy, ruff  
**Storage**: Filesystem — `.kittify/config.yaml` (activation state), `src/charter/packs/default.yaml` (shipped pack template), `.kittify/charter/backups/` (upgrade backup)  
**Testing**: pytest with `fast`, `doctrine`, `architectural` marks; `pytestarch` for layer rules; `pytest-benchmark` for NFR-001 real-I/O performance  
**Target Platform**: Linux/macOS/Windows (cross-platform, path handling via pathlib)  
**Project Type**: Single Python package (`src/` layout)  
**Performance Goals**: Charter activation read path ≤ 100ms p99 under real filesystem I/O (NFR-001); use multi-run percentile measurement, not single wall-clock check  
**Constraints**: Strict layer rule — `doctrine.*` must never import `charter.*`; `specify_cli.*` may import both; all activation state changes go through `charter.*` APIs  
**Scale/Scope**: Per-project activation state (small YAML); shipped pack is static YAML; upgrade path is single-pass migration

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter loaded from `.kittify/charter/charter.md`. Key governance directives that apply:

| Directive | Relevance |
|-----------|-----------|
| DIR-001 Domain isolation | `doctrine.*` ← `charter.*` direction is forbidden; activation filtering lives in `charter.*` |
| DIR-002 Hard restriction model | Explicit activations override defaults; no implicit fallback when activation entry is present |
| DIR-004 Backward compatibility | Default charter pack must fully populate all 9 kinds so existing users lose nothing |
| DIR-006 Atomic upgrade | Backup-before-write pattern for charter upgrade; resumable if interrupted |
| DIR-008 Testability | Wiring verification FRs (FR-031–FR-037) require grep-verifiable production call sites |
| DIR-013 Wiring discipline | Every new module must have a verified call site before the WP is considered done |

No charter violations in the planned design. DRG filtering remains in `charter.*` (correct side of the boundary). `doctrine.drg` is unchanged (returns unfiltered full DRG).

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-pack-activation-layer-01KSYE4V/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── charter-activate-cli.md
│   ├── charter-deactivate-cli.md
│   ├── charter-list-cli.md
│   └── charter-pack-consistency-check-cli.md
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── pack_context.py           # PackContext — reads activated_kinds from config.yaml
│   ├── drg.py                    # filter_graph_by_activation — WIRE THIS (FR-035)
│   ├── activations.py            # Per-action artifact registry (unchanged)
│   ├── invocation_context.py     # NEW — ProjectContext, OperationalContext, ContextPreconditionError (FR-040)
│   ├── packs/
│   │   └── default.yaml          # NEW — shipped default activation pack (all built-ins)
│   ├── pack_manager.py           # NEW — CharterPackManager: load/save/merge pack state
│   └── consistency_check.py      # NEW — charter pack consistency-check logic
├── doctrine/
│   ├── drg/                      # Unchanged — returns full unfiltered DRG
│   └── missions/
│       └── mission_step_repository.py  # Fix TYPE_CHECKING import (C-004 violation)
└── specify_cli/
    ├── charter_activate.py       # Refactor: write to config.yaml (fix reader gap)
    ├── upgrade/
    │   └── migrations/
    │       └── m_3_2_8_default_charter_pack.py   # NEW — upgrade migration
    └── cli/
        └── commands/
            └── charter/
                ├── activate.py   # Extend to all 9 kinds + --cascade
                ├── deactivate.py # NEW — first-class deactivate command
                └── pack.py       # NEW — charter pack subgroup (consistency-check)

tests/
├── architectural/
│   ├── test_layer_rules.py                           # Fix namespace package false positive
│   ├── test_template_governance_payload_contract.py  # Fix 8 broken tests (deleted paths)
│   ├── test_no_dead_modules.py                       # Add WP12 migration to allowlist
│   └── test_no_dead_symbols.py                       # Wire or allowlist 12 dead symbols
├── charter/
│   ├── test_pack_manager.py      # NEW
│   ├── test_invocation_context.py # NEW — ProjectContext.from_repo(), guard methods, ContextPreconditionError
│   ├── test_drg_filtering.py     # NEW — production wiring tests (FR-035)
│   └── test_consistency_check.py # NEW
├── specify_cli/
│   └── cli/commands/charter/
│       ├── test_charter_activate_commands.py  # Extend with all 9 kinds
│       ├── test_charter_deactivate_commands.py # NEW
│       └── test_charter_pack_commands.py       # NEW
└── specify_cli/next/
    └── test_runtime_bridge_dispatch.py  # Fix mock-only NFR-001 performance test
```

**Structure Decision**: Single Python package (`src/` layout). All activation layer changes extend or fix existing `charter.*` and `specify_cli.*` packages. No new top-level packages.

## Complexity Tracking

| Concern | Why Present | Approach |
|---------|-------------|----------|
| 9 artifact kinds, 3 resolution patterns | Kinds use different resolution paths (DRG, flat catalog, direct repo) | Pattern-A/B/C wiring table in research.md; common `PackContext` read API for all |
| Backward-compatibility on upgrade | Existing projects with no activation config must lose nothing | Default pack ships fully-populated; `from_config()` fallback already handles absent keys |
| Cascade semantics (activate vs deactivate differ) | Activation pulls in references; deactivation only removes exclusively-owned artifacts | Separate `_cascade_activate` / `_cascade_deactivate` helpers with shared-artifact protection |
| `mission-type` YAML key is `mission_type_activations` | Phase 1 used a different naming convention; all other kinds use `activated_<kind>` | Use explicit `YAML_KEY_MAP` dict in CharterPackManager (see data-model.md); do NOT use a generic formatter |
| `activated_kinds`/`mission_type_activations` retain two-state reader semantics | Backward compat: `[]` → all built-ins for these two grandfathered keys | New per-kind readers use three-state; add comment to `pack_context.py` explaining the asymmetry |

## Phase 0: Research Agenda

Research tasks dispatched from unknowns in Technical Context:

1. **Activation state storage consolidation** — `charter activate` writes override files; `PackContext.from_config()` reads config.yaml. Confirm: write directly to config.yaml `activated_kinds`/`mission_type_activations` keys and retire the override-files write path.

2. **Resolution pattern wiring map** — For each of the 3 patterns (A: DRG-based, B: flat catalog, C: direct repository), identify exact call sites that need to receive `PackContext` and call `filter_graph_by_activation` or equivalent filter. Document file + function + argument injection point for each.

3. **Upgrade migration design** — Confirm the `spec-kitty upgrade` hook point, backup strategy (copy `.kittify/charter/charter.md` to `.kittify/charter/backups/charter-<timestamp>.md`), and merge-defaults algorithm. Check if `ruamel.yaml` round-trip preserves comments.

4. **`MissionStepRepository` wiring** — Identify the production caller that should instantiate and use it via the `charter` facade. Confirm `charter.mission_steps` re-export path.

5. **`PackContext.activated_kinds` read sites** — Grep all resolution paths that should but currently don't read `activated_kinds`. Enumerate which functions receive `PackContext` vs which need to start receiving it.

**Output**: `research.md` with confirmed wiring table (kind → resolution pattern → call site → fix), storage decision, and upgrade algorithm.

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete with confirmed wiring table.

### Data Model

Key entities (detail in `data-model.md`):

- **`CharterPack`**: Immutable value object. Contains `activated_mission_types`, `activated_kinds`, and per-kind artifact lists (`activated_directives`, `activated_tactics`, etc.). Deserialized from `src/charter/packs/default.yaml`.
- **`PackContext`** (existing, extended): Gains `activated_directives`, `activated_tactics`, `activated_styleguides`, `activated_toolguides`, `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`, `activated_mission_step_contracts` — each a `frozenset[str] | None` (None = all built-ins available). Read from config.yaml; written by `charter activate/deactivate`.
- **`ActivationKind`**: Enum or Literal over the 9 activatable kinds (singular form used in CLI, plural in `PackContext`).
- **`CascadeScope`**: Parsed from the `--cascade` flag. Accepts `"all"` or any comma-separated set of CLI kind names (`"directive"`, `"tactic"`, `"styleguide"`, `"toolguide"`, `"paradigm"`, `"procedure"`, `"agent-profile"`, `"mission-step-contract"`). Absent flag = no cascade.
- **`ConsistencyReport`**: Result of `charter pack consistency-check` — list of coherent/incoherent entries, missing artifacts, unknown references.
- **`CharterBackup`**: Metadata record written alongside backup file: original path, backup path, timestamp, trigger.

### API Contracts

CLI contracts generated to `contracts/`:

1. `charter-activate-cli.md` — `charter activate <kind> <id> [--cascade <scope>]`
2. `charter-deactivate-cli.md` — `charter deactivate <kind> <id> [--cascade <scope>]`
3. `charter-list-cli.md` — `charter list [--show-available]`
4. `charter-pack-consistency-check-cli.md` — `charter pack consistency-check`

### Quickstart

`quickstart.md` covers: new project upgrade, existing-charter upgrade with backup, activate/deactivate with and without cascade, consistency-check, and WP lifecycle gate failures.
